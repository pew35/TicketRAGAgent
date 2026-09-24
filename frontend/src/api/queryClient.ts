import { QueryClient } from "@tanstack/react-query";

// Shared TanStack Query client for server state caching.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});
