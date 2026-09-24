import { create } from "zustand";
import { persist } from "zustand/middleware";

// Auth store keeps tokens and minimal login state across page reloads.
type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  setTokens: (accessToken: string, refreshToken?: string) => void;
  setAccessToken: (accessToken: string) => void;
  logout: () => void;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken: refreshToken ?? null }),
      setAccessToken: (accessToken) => set({ accessToken }),
      logout: () => set({ accessToken: null, refreshToken: null }),
    }),
    { name: "ticket-rag-auth" },
  ),
);
