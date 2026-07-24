import { create } from "zustand";
import { persist } from "zustand/middleware";
import { api } from "./kyClient";

// ──────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────
export interface User {
  id: string;
  userId: string;
  username: string;
  is_active: boolean;
  email?: string;
  [key: string]: any;
}

export type AuthUser = User;

export type AuthStatus = "initializing" | "authenticated" | "guest";

interface AuthState {
  user: AuthUser | null;
  token: string | null;
  status: AuthStatus;

  // Actions
  login: (user: AuthUser, token: string) => void;
  logout: () => void;
  setToken: (token: string) => void;
  initialize: () => Promise<void>;
}

// ──────────────────────────────────────────────────────────
// Initialization mutex
// Prevents concurrent initialize() calls (e.g. React 18
// StrictMode double-mount or fast route transitions).
// ──────────────────────────────────────────────────────────
let initPromise: Promise<void> | null = null;

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      status: "initializing",

      // ─── login ─────────────────────────────────────────
      login: (user, token) => {
        set({
          user,
          token,
          status: "authenticated",
        });
      },

      // ─── setToken ─────────────────────────────────────
      // Used by the ky refresh hook to swap in a new access
      // token without touching user / status.
      setToken: (token) => {
        set({ token });
      },

      // ─── logout ────────────────────────────────────────
      // Client-side state is cleared immediately.
      // We also fire-and-forget a server call so the
      // refresh-token cookie gets revoked.
      logout: () => {
        set({ user: null, token: null, status: "guest" });

        // Use a raw fetch to avoid circular import /
        // interceptor issues — this is fire-and-forget.
        fetch("http://localhost:8000/v1/auth/logout", {
          method: "POST",
          credentials: "include",
        }).catch(() => {
          // Swallow — if the server is down the cookie
          // will expire on its own.
        });
      },

      // ─── initialize ───────────────────────────────────
      // Called once on app mount. Validates the persisted
      // access token via /auth/me, and if that returns 401
      // the ky interceptor will automatically try /refresh
      // before giving up.
      initialize: async () => {
        // De-duplicate concurrent calls
        if (initPromise) return initPromise;

        initPromise = (async () => {
          const { token } = get();

          // No stored token at all → guest immediately
          if (!token) {
            set({ user: null, status: "guest" });
            return;
          }

          try {
            // This call goes through `api` which has the
            // afterResponse hook. If the access token is
            // expired, the hook will:
            //   1. Call POST /auth/refresh (via rawApi)
            //   2. Store the new token via setToken()
            //   3. Retry this GET /auth/me with the new token
            // If refresh also fails → hook calls logout()
            const user = await api.get("auth/me").json<AuthUser>();
            set({ user, status: "authenticated" });
          } catch {
            // If we land here, the interceptor already
            // tried refresh and it failed → we're logged out.
            // Make sure state is clean.
            const { status } = get();
            if (status !== "guest") {
              set({ user: null, token: null, status: "guest" });
            }
          }
        })();

        try {
          await initPromise;
        } finally {
          initPromise = null;
        }
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({ token: state.token }),
    }
  )
);
