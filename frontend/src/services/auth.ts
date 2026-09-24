import { useAuthStore } from "../stores/authStore";
import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  User,
} from "../types/api";
import request from "../utils/request";

// Authentication service keeps auth-related API calls and session actions together.
export async function login(data: LoginRequest): Promise<TokenResponse> {
  const tokens = await request.post<TokenResponse, LoginRequest>(
    "/api/users/login",
    data,
  );

  useAuthStore
    .getState()
    .setTokens(tokens.access_token, tokens.refresh_token);

  return tokens;
}

export function register(data: RegisterRequest): Promise<User> {
  return request.post<User, RegisterRequest>("/api/users/register", data);
}

export function getCurrentUser(): Promise<User> {
  return request.get<User>("/api/users/me");
}

export function logout(): void {
  useAuthStore.getState().logout();

  if (typeof window !== "undefined") {
    window.location.assign(`${import.meta.env.BASE_URL}login`);
  }
}

export function isAuthenticated(): boolean {
  return Boolean(useAuthStore.getState().accessToken);
}
