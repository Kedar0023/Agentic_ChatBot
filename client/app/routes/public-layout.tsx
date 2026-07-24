import { Navigate, Outlet } from "react-router";
import { useAuthStore } from "@/lib/ZustandStore";

/**
 * Guard for public-only routes (login, register).
 * Redirects authenticated users away from auth pages.
 * Root.tsx guarantees status is resolved before this renders.
 */
export default function PublicLayout() {
  const status = useAuthStore((state) => state.status);

  if (status === "authenticated") {
    return <Navigate to="/home" replace />;
  }

  return <Outlet />;
}
