import axios from "axios";

import { ErrorCode, getErrorMessage, isSuccess } from "./errorCodes";

// ApiResponse mirrors the server's code, message, and data response envelope.
export type ApiResponse<T> = {
  code: number;
  message: string;
  data: T | null;
};

type ApiErrorOptions = {
  code: number;
  message: string;
  httpStatus?: number;
  data?: unknown;
  originalError?: unknown;
};

// ApiError preserves both the HTTP status and application error code.
export class ApiError extends Error {
  readonly code: number;
  readonly httpStatus?: number;
  readonly data?: unknown;
  readonly originalError?: unknown;

  constructor({ code, message, httpStatus, data, originalError }: ApiErrorOptions) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.httpStatus = httpStatus;
    this.data = data;
    this.originalError = originalError;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

// Return whether an unknown value follows the backend response envelope.
export function isApiResponse<T = unknown>(value: unknown): value is ApiResponse<T> {
  if (!value || typeof value !== "object") {
    return false;
  }

  const response = value as Record<string, unknown>;
  return (
    typeof response.code === "number" &&
    typeof response.message === "string" &&
    Object.prototype.hasOwnProperty.call(response, "data")
  );
}

// Return whether an unknown value is the normalized frontend API error.
export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

// Extract successful business data or throw a normalized application error.
export function extractResponseData<T>(response: ApiResponse<T>, httpStatus?: number): T {
  if (!isSuccess(response.code)) {
    throw createApiError(response, httpStatus);
  }

  return response.data as T;
}

// Build an ApiError from a backend response envelope.
export function createApiError(
  response: ApiResponse<unknown>,
  httpStatus?: number,
  originalError?: unknown,
): ApiError {
  return new ApiError({
    code: response.code,
    message: response.message || getErrorMessage(response.code),
    httpStatus,
    data: response.data,
    originalError,
  });
}

// Extract the most specific human-readable message available from an error.
export function extractErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    return error.message;
  }

  if (axios.isAxiosError(error)) {
    const responseData = error.response?.data;
    if (isApiResponse(responseData)) {
      return responseData.message || getErrorMessage(responseData.code);
    }

    if (responseData && typeof responseData === "object") {
      const detail = (responseData as Record<string, unknown>).detail;
      if (typeof detail === "string") {
        return detail;
      }
      if (isApiResponse(detail)) {
        return detail.message || getErrorMessage(detail.code);
      }
    }

    if (error.code === "ECONNABORTED") {
      return "The request timed out.";
    }

    if (!error.response) {
      return "Unable to connect to the server.";
    }

    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return getErrorMessage(ErrorCode.UNKNOWN_ERROR);
}

// Convert Axios, backend, and JavaScript errors into one predictable error type.
export function normalizeApiError(error: unknown): ApiError {
  if (isApiError(error)) {
    return error;
  }

  if (axios.isAxiosError(error)) {
    const responseData = error.response?.data;
    if (isApiResponse(responseData)) {
      return createApiError(responseData, error.response?.status, error);
    }

    if (responseData && typeof responseData === "object") {
      const detail = (responseData as Record<string, unknown>).detail;
      if (isApiResponse(detail)) {
        return createApiError(detail, error.response?.status, error);
      }
    }

    const code = error.code === "ECONNABORTED"
      ? ErrorCode.EXTERNAL_SERVICE_TIMEOUT
      : error.response
        ? ErrorCode.UNKNOWN_ERROR
        : ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE;

    return new ApiError({
      code,
      message: extractErrorMessage(error),
      httpStatus: error.response?.status,
      data: responseData,
      originalError: error,
    });
  }

  return new ApiError({
    code: ErrorCode.UNKNOWN_ERROR,
    message: extractErrorMessage(error),
    originalError: error,
  });
}
