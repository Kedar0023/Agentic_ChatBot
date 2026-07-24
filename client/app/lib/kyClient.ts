import ky from "ky";
import { useAuthStore } from "./ZustandStore";

const API_BASE = "http://localhost:8000/v1";

// ──────────────────────────────────────────────────────────
// Raw API instance — NO interceptors.
// Used exclusively for /auth/refresh so that a 401 from the
// refresh endpoint itself does NOT trigger another refresh
// (which would create an infinite loop).
// ──────────────────────────────────────────────────────────
const rawApi = ky.create({
  prefix: API_BASE,
  credentials: "include",
  headers: { "Content-Type": "application/json" },
});

// ──────────────────────────────────────────────────────────
// Refresh mutex
// Only ONE refresh request can be in-flight at any time.
// Every concurrent 401 awaits this same promise instead of
// spawning its own refresh call (race condition prevention).
// ──────────────────────────────────────────────────────────
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  // If a refresh is already in-flight, piggyback on it
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const res = await rawApi
        .post("auth/refresh")
        .json<{
          message: string;
          userId: string;
          username: string;
          access_token: string;
        }>();

      const { setToken } = useAuthStore.getState();
      setToken(res.access_token);
      return res.access_token;
    } catch {
      // Refresh failed (expired / revoked / missing cookie) → full logout
      useAuthStore.getState().logout();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

// ──────────────────────────────────────────────────────────
// Public API instance — used by all app code
// ──────────────────────────────────────────────────────────
export const api = ky.create({
  prefix: API_BASE,
  credentials: "include",
  headers: { "Content-Type": "application/json" },
  hooks: {
    beforeRequest: [
      ({ request }) => {
        const token = useAuthStore.getState().token;
        if (token) {
          request.headers.set("Authorization", `Bearer ${token}`);
        }
      },
    ],
    afterResponse: [
      async ({ request, options, response }) => {
        if (response.status !== 401) return;

        // Don't try to refresh auth endpoints to prevent loops
        const url = new URL(response.url);
        const authPaths = ["auth/login", "auth/register", "auth/refresh", "auth/logout"];
        if (authPaths.some((p) => url.pathname.includes(p))) {
          return;
        }

        // Attempt one refresh
        const newToken = await refreshAccessToken();

        if (!newToken) {
          // Refresh failed — already logged out inside refreshAccessToken()
          return;
        }

        // Retry the original request with the fresh token
        request.headers.set("Authorization", `Bearer ${newToken}`);
        return ky(request, options);
      },
    ],
  },
});
