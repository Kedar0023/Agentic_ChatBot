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

export interface ChatThread {
  id: string;
  title: string;
  category: "Today" | "Yesterday" | "Previous 7 Days" | "Older";
  updatedAt?: string;
  created_at?: string;
  isPinned?: boolean;
}

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
      setToken: (token) => {
        set({ token });
      },

      // ─── logout ────────────────────────────────────────
      logout: () => {
        set({ user: null, token: null, status: "guest" });

        fetch("http://localhost:8000/v1/auth/logout", {
          method: "POST",
          credentials: "include",
        }).catch(() => {});
      },

      // ─── initialize ───────────────────────────────────
      initialize: async () => {
        if (initPromise) return initPromise;

        initPromise = (async () => {
          const { token } = get();

          if (!token) {
            set({ user: null, status: "guest" });
            return;
          }

          try {
            const user = await api.get("auth/me").json<AuthUser>();
            set({ user, status: "authenticated" });
          } catch {
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

// ──────────────────────────────────────────────────────────
// Sidebar / UI State Store with API integration
// ──────────────────────────────────────────────────────────
export interface SidebarUIState {
  isCollapsed: boolean;
  isMobileOpen: boolean;
  searchQuery: string;
  userMenuOpen: boolean;
  activeTabMenuId: string | null;
  activeThreadId: string | null;
  threads: ChatThread[];
  isLoadingThreads: boolean;

  // Actions
  setIsCollapsed: (collapsed: boolean | ((prev: boolean) => boolean)) => void;
  toggleCollapse: () => void;
  setMobileOpen: (open: boolean | ((prev: boolean) => boolean)) => void;
  toggleMobileOpen: () => void;
  openMobileSidebar: () => void;
  closeMobileSidebar: () => void;
  setSearchQuery: (query: string) => void;
  setUserMenuOpen: (open: boolean | ((prev: boolean) => boolean)) => void;
  toggleUserMenu: () => void;
  setActiveTabMenuId: (id: string | null | ((prev: string | null) => string | null)) => void;
  setActiveThreadId: (id: string | null) => void;
  resetSidebarUI: () => void;

  // API Actions
  fetchThreads: () => Promise<void>;
  createThread: () => Promise<string | null>;
  updateThreadTitle: (threadId: string, title: string) => Promise<void>;
  deleteThread: (threadId: string) => Promise<void>;
}

export const useSidebarStore = create<SidebarUIState>()(
  persist(
    (set, get) => ({
      isCollapsed: false,
      isMobileOpen: false,
      searchQuery: "",
      userMenuOpen: false,
      activeTabMenuId: null,
      activeThreadId: null,
      threads: [],
      isLoadingThreads: false,

      setIsCollapsed: (collapsed) =>
        set((state) => ({
          isCollapsed: typeof collapsed === "function" ? collapsed(state.isCollapsed) : collapsed,
        })),

      toggleCollapse: () =>
        set((state) => ({
          isCollapsed: !state.isCollapsed,
        })),

      setMobileOpen: (open) =>
        set((state) => ({
          isMobileOpen: typeof open === "function" ? open(state.isMobileOpen) : open,
        })),

      toggleMobileOpen: () =>
        set((state) => ({
          isMobileOpen: !state.isMobileOpen,
        })),

      openMobileSidebar: () => set({ isMobileOpen: true }),
      closeMobileSidebar: () => set({ isMobileOpen: false }),

      setSearchQuery: (searchQuery) => set({ searchQuery }),

      setUserMenuOpen: (open) =>
        set((state) => ({
          userMenuOpen: typeof open === "function" ? open(state.userMenuOpen) : open,
        })),

      toggleUserMenu: () =>
        set((state) => ({
          userMenuOpen: !state.userMenuOpen,
        })),

      setActiveTabMenuId: (activeTabMenuId) =>
        set((state) => ({
          activeTabMenuId:
            typeof activeTabMenuId === "function"
              ? activeTabMenuId(state.activeTabMenuId)
              : activeTabMenuId,
        })),

      setActiveThreadId: (activeThreadId) => set({ activeThreadId }),

      resetSidebarUI: () =>
        set({
          isMobileOpen: false,
          searchQuery: "",
          userMenuOpen: false,
          activeTabMenuId: null,
        }),

      // ── API Actions ─────────────────────────────────────
      fetchThreads: async () => {
        set({ isLoadingThreads: true });
        try {
          const data = await api
            .get("chat/base/get_all_thread_titles")
            .json<Array<{ id: string; title: string; created_at?: string; updated_at?: string }>>();

          const formattedThreads: ChatThread[] = data.map((t) => ({
            id: t.id,
            title: t.title || "Untitled Chat",
            category: "Today",
            updatedAt: t.updated_at || t.created_at || "Recently",
          }));

          set({ threads: formattedThreads, isLoadingThreads: false });
        } catch (error) {
          console.error("Failed to fetch thread titles from API:", error);
          set({ isLoadingThreads: false });
        }
      },

      createThread: async () => {
        try {
          const res = await api.post("chat/new_thread").json<{ thread_id: string }>();
          const newThread: ChatThread = {
            id: res.thread_id,
            title: "New Chat",
            category: "Today",
            updatedAt: "Just now",
          };

          set((state) => ({
            threads: [newThread, ...state.threads],
            activeThreadId: res.thread_id,
          }));

          return res.thread_id;
        } catch (error) {
          console.error("Failed to create thread via API:", error);
          return null;
        }
      },

      updateThreadTitle: async (threadId: string, title: string) => {
        // Optimistic state update
        set((state) => ({
          threads: state.threads.map((t) => (t.id === threadId ? { ...t, title } : t)),
        }));

        try {
          await api.patch(`chat/base/${threadId}/title`, { json: { title } }).json();
        } catch (error) {
          console.error("Failed to update thread title via API:", error);
          get().fetchThreads();
        }
      },

      deleteThread: async (threadId: string) => {
        // Optimistic state deletion
        set((state) => ({
          threads: state.threads.filter((t) => t.id !== threadId),
        }));

        try {
          await api.delete(`chat/base/${threadId}`).json();
        } catch (error) {
          console.error("Failed to delete thread via API:", error);
          get().fetchThreads();
        }
      },
    }),
    {
      name: "sidebar-ui-storage",
      partialize: (state) => ({ isCollapsed: state.isCollapsed }),
    }
  )
);


