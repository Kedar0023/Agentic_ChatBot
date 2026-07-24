import { Navigate, Outlet } from "react-router";
import { useAuthStore } from "@/lib/ZustandStore";

/**
 * Guard for protected routes.
 * By the time this renders, root.tsx has already resolved
 * the auth status (it gates <Outlet> behind initialization),
 * so `status` will always be either "authenticated" or "guest" — never "initializing".
 */
export default function ProtectedLayout() {
  const status = useAuthStore((state) => state.status);

  if (status !== "authenticated") {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
