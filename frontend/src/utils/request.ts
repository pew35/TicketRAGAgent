import axios, {
  AxiosHeaders,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";

import { useAuthStore } from "../stores/authStore";
import type { TokenResponse } from "../types/api";
import {
  ErrorCode,
  isAuthError,
  isSuccess,
} from "./errorCodes";
import {
  ApiError,
  createApiError,
  extractResponseData,
  isApiResponse,
  normalizeApiError,
  type ApiResponse,
} from "./response";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const DEFAULT_TIMEOUT_MS = 30_000;
const REFRESH_TIMEOUT_MS = 15_000;
const REFRESH_PATH = "/api/users/refresh";
const PUBLIC_AUTH_PATHS = new Set([
  "/api/users/login",
  "/api/users/register",
  "/api/users/refresh",
]);

export type RequestConfig<Data = unknown> = AxiosRequestConfig<Data> & {
  skipAuth?: boolean;
  skipAuthRefresh?: boolean;
  skipResponseTransform?: boolean;
  _retry?: boolean;
};

type ManagedRequestConfig = InternalAxiosRequestConfig & {
  skipAuth?: boolean;
  skipAuthRefresh?: boolean;
  skipResponseTransform?: boolean;
  _retry?: boolean;
};

// The intercepted client handles authenticated application API requests.
export const httpClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: DEFAULT_TIMEOUT_MS,
});

// Refresh requests use a bare client to prevent recursive refresh interception.
const refreshClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: REFRESH_TIMEOUT_MS,
});

let refreshPromise: Promise<string> | null = null;

httpClient.interceptors.request.use((config) => {
  const managedConfig = config as ManagedRequestConfig;
  if (managedConfig.skipAuth || isPublicAuthRequest(managedConfig.url)) {
    return managedConfig;
  }

  const accessToken = useAuthStore.getState().accessToken;
  if (accessToken) {
    managedConfig.headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return managedConfig;
});

httpClient.interceptors.response.use(
  (response) => {
    const config = response.config as ManagedRequestConfig;
    if (config.skipResponseTransform) {
      return response;
    }

    if (!isApiResponse(response.data)) {
      return Promise.reject(
        new ApiError({
          code: ErrorCode.UNKNOWN_ERROR,
          message: "The server returned an invalid response format.",
          httpStatus: response.status,
          data: response.data,
        }),
      );
    }

    if (!isSuccess(response.data.code)) {
      const apiError = createApiError(response.data, response.status);
      if (shouldClearSession(apiError.code) && !isPublicAuthRequest(config.url)) {
        clearSessionAndRedirect();
      }
      return Promise.reject(apiError);
    }

    response.data = extractResponseData(response.data, response.status);
    return response;
  },
  async (error: unknown) => {
    const apiError = normalizeApiError(error);
    const originalConfig = axios.isAxiosError(error)
      ? error.config as ManagedRequestConfig | undefined
      : undefined;

    if (originalConfig && isPublicAuthRequest(originalConfig.url)) {
      return Promise.reject(apiError);
    }

    const shouldRefresh =
      apiError.httpStatus === 401 &&
      originalConfig !== undefined &&
      !originalConfig._retry &&
      !originalConfig.skipAuthRefresh;

    if (shouldRefresh) {
      const refreshToken = useAuthStore.getState().refreshToken;
      if (!refreshToken) {
        clearSessionAndRedirect();
        return Promise.reject(apiError);
      }

      originalConfig._retry = true;

      try {
        const accessToken = await getRefreshedAccessToken();
        originalConfig.headers = AxiosHeaders.from(originalConfig.headers);
        originalConfig.headers.set("Authorization", `Bearer ${accessToken}`);
        return httpClient.request(originalConfig);
      } catch (refreshError) {
        clearSessionAndRedirect();
        return Promise.reject(normalizeApiError(refreshError));
      }
    }

    if (shouldClearSession(apiError.code)) {
      clearSessionAndRedirect();
    }

    return Promise.reject(apiError);
  },
);

async function getRefreshedAccessToken(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = performAccessTokenRefresh().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}

async function performAccessTokenRefresh(): Promise<string> {
  const authState = useAuthStore.getState();
  if (!authState.refreshToken) {
    throw new ApiError({
      code: ErrorCode.INVALID_REFRESH_TOKEN,
      message: "A refresh token is required.",
    });
  }

  const response = await refreshClient.post<ApiResponse<TokenResponse>>(REFRESH_PATH, {
    refresh_token: authState.refreshToken,
  });
  const tokens = extractResponseData(response.data, response.status);

  if (!tokens.access_token) {
    throw new ApiError({
      code: ErrorCode.INVALID_ACCESS_TOKEN,
      message: "The refresh response did not include an access token.",
      httpStatus: response.status,
      data: response.data,
    });
  }

  authState.setTokens(tokens.access_token, tokens.refresh_token ?? authState.refreshToken);
  return tokens.access_token;
}

// Share the same deduplicated refresh operation with non-Axios transports such as SSE.
export function refreshAccessToken(): Promise<string> {
  return getRefreshedAccessToken();
}

function shouldClearSession(code: number): boolean {
  if (!isAuthError(code) && code !== ErrorCode.USER_DISABLED) {
    return false;
  }

  return ![
    ErrorCode.INVALID_CREDENTIALS,
    ErrorCode.PERMISSION_DENIED,
    ErrorCode.SUPERUSER_REQUIRED,
    ErrorCode.EMAIL_NOT_VERIFIED,
    ErrorCode.PASSWORD_TOO_WEAK,
  ].includes(code as ErrorCode);
}

function isPublicAuthRequest(url?: string): boolean {
  return PUBLIC_AUTH_PATHS.has(getRequestPath(url));
}

function getRequestPath(url?: string): string {
  if (!url) {
    return "";
  }

  try {
    return new URL(url, API_BASE_URL).pathname;
  } catch {
    return url.split("?")[0];
  }
}

function clearSessionAndRedirect(): void {
  useAuthStore.getState().logout();

  const loginPath = `${import.meta.env.BASE_URL}login`;
  if (typeof window !== "undefined" && window.location.pathname !== loginPath) {
    window.location.replace(loginPath);
  }
}

async function sendRequest<ResponseData, RequestData = unknown>(
  config: RequestConfig<RequestData>,
): Promise<ResponseData> {
  const response = await httpClient.request<
    ApiResponse<ResponseData>,
    AxiosResponse<ResponseData>,
    RequestData
  >(config);
  return response.data;
}

async function get<ResponseData>(
  url: string,
  config: RequestConfig = {},
): Promise<ResponseData> {
  return sendRequest<ResponseData>({ ...config, method: "GET", url });
}

async function post<ResponseData, RequestData = unknown>(
  url: string,
  data?: RequestData,
  config: RequestConfig<RequestData> = {},
): Promise<ResponseData> {
  return sendRequest<ResponseData, RequestData>({ ...config, data, method: "POST", url });
}

async function put<ResponseData, RequestData = unknown>(
  url: string,
  data?: RequestData,
  config: RequestConfig<RequestData> = {},
): Promise<ResponseData> {
  return sendRequest<ResponseData, RequestData>({ ...config, data, method: "PUT", url });
}

async function patch<ResponseData, RequestData = unknown>(
  url: string,
  data?: RequestData,
  config: RequestConfig<RequestData> = {},
): Promise<ResponseData> {
  return sendRequest<ResponseData, RequestData>({ ...config, data, method: "PATCH", url });
}

async function deleteRequest<ResponseData>(
  url: string,
  config: RequestConfig = {},
): Promise<ResponseData> {
  return sendRequest<ResponseData>({ ...config, method: "DELETE", url });
}

async function raw<ResponseData, RequestData = unknown>(
  config: RequestConfig<RequestData>,
): Promise<AxiosResponse<ResponseData>> {
  const rawConfig: RequestConfig<RequestData> = {
    ...config,
    skipResponseTransform: true,
  };
  return httpClient.request<ResponseData, AxiosResponse<ResponseData>, RequestData>(rawConfig);
}

const request = {
  request: sendRequest,
  get,
  post,
  put,
  patch,
  delete: deleteRequest,
  raw,
};

export default request;
