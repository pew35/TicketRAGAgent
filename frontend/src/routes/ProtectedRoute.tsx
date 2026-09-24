import { Navigate } from "react-router-dom";

import { useAuthStore } from "../stores/authStore";

// ProtectedRoute redirects unauthenticated users away from app pages.
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const accessToken = useAuthStore((state) => state.accessToken);
  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }
  return children;
}
