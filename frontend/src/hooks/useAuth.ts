import { useQuery } from "@tanstack/react-query";

import { getCurrentUser, logout as endSession } from "../services/auth";

const currentUserKey = ["auth", "current-user"] as const;

// Keep current-user loading and session exit behind one small page-facing API.
export function useAuth() {
  const currentUserQuery = useQuery({
    queryKey: currentUserKey,
    queryFn: getCurrentUser,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  return {
    user: currentUserQuery.data ?? null,
    isLoading: currentUserQuery.isLoading,
    error: currentUserQuery.error,
    logout: endSession,
  };
}
