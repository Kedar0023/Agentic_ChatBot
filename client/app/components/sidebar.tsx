import React, { useState, useEffect, useMemo } from "react";
import { Link, useParams, useNavigate } from "react-router";
import {
  Plus,
  MessageSquare,
  Search,
  LogOut,
  Settings,
  Sun,
  Moon,
  PanelLeft,
  PanelLeftClose,
  MoreHorizontal,
  Trash2,
  Edit3,
  Pin,
  ChevronsUpDown,
  Sparkles,
  X,
  Menu,
  HelpCircle,
  Check,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import logo_dark from "@/assets/Dark_varient.svg";
import logo_light from "@/assets/light_varient.svg";
import { useAuthStore, useSidebarStore, type ChatThread } from "@/lib/ZustandStore";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/components/ThemeToggle";

export { useSidebarStore };
export type { ChatThread };

// ── Sub-components (Using Zustand state directly without props) ──

// 1. Sidebar Header (Brand Logo & Collapse Toggle)
function SidebarHeader() {
  const isCollapsed = useSidebarStore((state) => state.isCollapsed);
  const toggleCollapse = useSidebarStore((state) => state.toggleCollapse);

  return (
    <div className="flex items-center justify-between h-14 px-3 border-b border-sidebar-border/60">
      <Link
        to="/chat"
        className={cn(
          "flex items-center gap-2.5 font-semibold tracking-tight transition-opacity hover:opacity-90 overflow-hidden",
          isCollapsed && "justify-center w-full px-0"
        )}
        title="FinSpike AI AI"
      >
        {/* <div className="flex items-center justify-center size-8 rounded-xl bg-primary text-primary-foreground shadow-sm shrink-0">
          <Sparkles className="size-4" />
        </div> */}

        <img
          src={logo_dark}
          alt="FinSpike AI Logo"
          className="h-8 w-8 rounded-md dark:hidden shrink-0"
        />
        <img
          src={logo_light}
          alt="FinSpike AI Logo"
          className="h-8 w-8 rounded-md hidden dark:block shrink-0"
        />
        
        {!isCollapsed && (
          <span className="truncate text-base font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
            FinSpike AI
          </span>
        )}
      </Link>

      {!isCollapsed && (
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={toggleCollapse}
          className="hidden md:flex text-muted-foreground hover:text-foreground"
          title="Collapse Sidebar"
        >
          <PanelLeftClose className="size-4" />
        </Button>
      )}
    </div>
  );
}

// 2. New Chat Button & Search Bar (API POST /v1/chat/new_thread)
function SidebarActions() {
  const navigate = useNavigate();
  const isCollapsed = useSidebarStore((state) => state.isCollapsed);
  const searchQuery = useSidebarStore((state) => state.searchQuery);
  const setSearchQuery = useSidebarStore((state) => state.setSearchQuery);
  const closeMobileSidebar = useSidebarStore((state) => state.closeMobileSidebar);
  const createThread = useSidebarStore((state) => state.createThread);


  return (
    <div className="p-3 space-y-2">
      <Button
        onClick={() => {
          closeMobileSidebar();
          navigate("/chat");
        }}
        variant="default"
        className={cn(
          "w-full justify-start gap-2 shadow-xs transition-transform active:scale-[0.98]",
          isCollapsed ? "justify-center px-0 size-10 rounded-xl mx-auto" : "h-10 px-3.5 rounded-xl"
        )}
        title="New Chat"
      >
        <Plus className="size-4 shrink-0" />
        {!isCollapsed && <span className="font-medium text-sm">New Chat</span>}
      </Button>

      {!isCollapsed && (
        <div className="relative mt-2">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search chats..."
            className="w-full h-8 pl-8 pr-7 text-xs bg-sidebar-accent/50 rounded-lg border border-sidebar-border/60 focus:outline-none focus:ring-1 focus:ring-ring text-foreground placeholder:text-muted-foreground transition-all"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="size-3" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// 3. Thread Item & Options Dropdown Menu (API PATCH title & DELETE thread)
function SidebarThreadItem({ thread }: { thread: ChatThread }) {
  const params = useParams<{ thread_id?: string }>();
  const navigate = useNavigate();
  const activeThreadId = useSidebarStore((state) => state.activeThreadId);
  const activeTabMenuId = useSidebarStore((state) => state.activeTabMenuId);
  const setActiveTabMenuId = useSidebarStore((state) => state.setActiveTabMenuId);
  const closeMobileSidebar = useSidebarStore((state) => state.closeMobileSidebar);
  const updateThreadTitle = useSidebarStore((state) => state.updateThreadTitle);
  const deleteThread = useSidebarStore((state) => state.deleteThread);

  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(thread.title);

  const currentThreadId = activeThreadId || params.thread_id;
  const isActive = currentThreadId === thread.id;
  const isMenuOpen = activeTabMenuId === thread.id;

  const handleToggleMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setActiveTabMenuId(isMenuOpen ? null : thread.id);
  };

  const handleCloseMenu = () => {
    setActiveTabMenuId(null);
  };

  const handleStartRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsEditing(true);
    setEditTitle(thread.title);
    setActiveTabMenuId(null);
  };

  const handleSaveRename = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (editTitle.trim() && editTitle.trim() !== thread.title) {
      await updateThreadTitle(thread.id, editTitle.trim());
    }
    setIsEditing(false);
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    handleCloseMenu();
    await deleteThread(thread.id);
    if (currentThreadId === thread.id) {
      navigate("/chat");
    }
  };

  return (
    <div className="relative group">
      {isEditing ? (
        <form onSubmit={handleSaveRename} className="flex items-center gap-1 px-2 py-1">
          <input
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") setIsEditing(false);
            }}
            autoFocus
            className="w-full h-7 px-2 text-xs bg-sidebar-accent border border-sidebar-border rounded focus:outline-none focus:ring-1 focus:ring-ring text-foreground"
          />
          <button
            type="submit"
            className="p-1 text-primary hover:text-primary/80"
            title="Save Title"
          >
            <Check className="size-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setIsEditing(false)}
            className="p-1 text-muted-foreground hover:text-foreground"
            title="Cancel"
          >
            <X className="size-3.5" />
          </button>
        </form>
      ) : (
        <Link
          to={`/chat/${thread.id}`}
          onClick={closeMobileSidebar}
          className={cn(
            "flex items-center gap-2.5 px-2.5 py-2 text-xs rounded-lg transition-all group/item pr-8",
            isActive
              ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium shadow-2xs"
              : "text-sidebar-foreground/80 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
          )}
        >
          <MessageSquare
            className={cn(
              "size-3.5 shrink-0 transition-colors",
              isActive
                ? "text-primary"
                : "text-muted-foreground group-hover/item:text-sidebar-foreground"
            )}
          />
          <span className="truncate flex-1 text-xs">{thread.title}</span>
          {thread.isPinned && (
            <Pin className="size-3 text-muted-foreground shrink-0 fill-current opacity-70" />
          )}
        </Link>
      )}

      {/* Action menu trigger (visible on hover or active) */}
      {!isEditing && (
        <div
          className={cn(
            "absolute right-1.5 top-1/2 -translate-y-1/2 flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity",
            isMenuOpen && "opacity-100"
          )}
        >
          <button
            type="button"
            onClick={handleToggleMenu}
            className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-sidebar-border/40 transition-colors"
            title="Thread Options"
          >
            <MoreHorizontal className="size-3.5" />
          </button>
        </div>
      )}

      {/* Thread Dropdown Popup */}
      {isMenuOpen && !isEditing && (
        <div
          className="absolute right-2 top-8 w-36 py-1 bg-popover text-popover-foreground rounded-lg border border-border shadow-lg z-50 animate-in fade-in zoom-in-95"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            onClick={handleStartRename}
            className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs hover:bg-accent text-foreground transition-colors"
          >
            <Edit3 className="size-3" />
            Rename
          </button>
          <button
            type="button"
            onClick={handleCloseMenu}
            className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs hover:bg-accent text-foreground transition-colors"
          >
            <Pin className="size-3" />
            {thread.isPinned ? "Unpin" : "Pin"}
          </button>
          <div className="my-1 border-t border-border" />
          <button
            type="button"
            onClick={handleDelete}
            className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs hover:bg-destructive/10 text-destructive transition-colors"
          >
            <Trash2 className="size-3" />
            Delete
          </button>
        </div>
      )}
    </div>
  );
}

// 4. Previous Chat Titles List (API GET /v1/chat/base/get_all_thread_titles)
function SidebarThreadList() {
  const params = useParams<{ thread_id?: string }>();
  const isCollapsed = useSidebarStore((state) => state.isCollapsed);
  const searchQuery = useSidebarStore((state) => state.searchQuery);
  const activeThreadId = useSidebarStore((state) => state.activeThreadId);
  const closeMobileSidebar = useSidebarStore((state) => state.closeMobileSidebar);
  const storeThreads = useSidebarStore((state) => state.threads);
  const fetchThreads = useSidebarStore((state) => state.fetchThreads);
  const isLoadingThreads = useSidebarStore((state) => state.isLoadingThreads);

  useEffect(() => {
    fetchThreads();
  }, [fetchThreads]);

  const currentThreadId = activeThreadId || params.thread_id;
  const threadsToDisplay = storeThreads;

  const filteredThreads = useMemo(() => {
    if (!searchQuery.trim()) return threadsToDisplay;
    return threadsToDisplay.filter((t) =>
      t.title.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [searchQuery, threadsToDisplay]);

  const categories: ChatThread["category"][] = [
    "Today",
    "Yesterday",
    "Previous 7 Days",
    "Older",
  ];

  const groupedThreads = useMemo(() => {
    const groups: Record<string, ChatThread[]> = {};
    categories.forEach((cat) => (groups[cat] = []));
    filteredThreads.forEach((thread) => {
      const cat = thread.category || "Today";
      if (groups[cat]) {
        groups[cat].push(thread);
      } else {
        groups["Older"].push(thread);
      }
    });
    return groups;
  }, [filteredThreads]);

  return (
    <div className="flex-1 overflow-y-auto px-2 py-1 space-y-4 scrollbar-thin scrollbar-thumb-sidebar-border">
      {isLoadingThreads && storeThreads.length === 0 ? (
        <div className="flex items-center justify-center py-6 text-muted-foreground">
          <Loader2 className="size-4 animate-spin mr-2" />
          <span className="text-xs">Loading threads...</span>
        </div>
      ) : isCollapsed ? (
        // Collapsed View Icon List
        <div className="flex flex-col items-center gap-1.5 py-2">
          {threadsToDisplay.slice(0, 6).map((thread) => {
            const isActive = currentThreadId === thread.id;
            return (
              <Link
                key={thread.id}
                to={`/chat/${thread.id}`}
                onClick={closeMobileSidebar}
                className={cn(
                  "flex items-center justify-center size-9 rounded-lg transition-colors relative group",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
                )}
                title={thread.title}
              >
                <MessageSquare className="size-4" />
                {/* Tooltip on hover for collapsed mode */}
                <div className="absolute left-full ml-2 px-2.5 py-1 bg-popover text-popover-foreground text-xs rounded-md shadow-md whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none z-50 transition-opacity">
                  {thread.title}
                </div>
              </Link>
            );
          })}
        </div>
      ) : (
        // Expanded View Categorized List
        categories.map((category) => {
          const threads = groupedThreads[category];
          if (!threads || threads.length === 0) return null;

          return (
            <div key={category} className="space-y-1">
              <div className="px-2.5 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                {category}
              </div>
              <div className="space-y-0.5">
                {threads.map((thread) => (
                  <SidebarThreadItem key={thread.id} thread={thread} />
                ))}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}

// 5. Bottom User Profile & Options Popover
function SidebarUserMenu() {
  const isCollapsed = useSidebarStore((state) => state.isCollapsed);
  const userMenuOpen = useSidebarStore((state) => state.userMenuOpen);
  const setUserMenuOpen = useSidebarStore((state) => state.setUserMenuOpen);
  const toggleUserMenu = useSidebarStore((state) => state.toggleUserMenu);

  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const { theme, setTheme } = useTheme();

  const displayName = user?.username || user?.name || "test User";
  const displayEmail = user?.email || "user@agentic.ai";
  const userInitials = displayName
    .split(" ")
    .map((n: string) => n[0])
    .join("")
    .substring(0, 2)
    .toUpperCase();

  return (
    <div className="p-2 border-t border-sidebar-border/60 bg-sidebar relative">
      {/* User Popover / Dropdown Card */}
      {userMenuOpen && (
        <div
          className={cn(
            "absolute bottom-full mb-2 bg-popover text-popover-foreground border border-border rounded-xl shadow-xl z-50 p-2 animate-in fade-in slide-in-from-bottom-2",
            isCollapsed ? "left-2 w-56" : "left-2 right-2"
          )}
        >
          {/* User Profile Header Info */}
          <div className="flex items-center gap-2.5 p-2 rounded-lg bg-muted/40">
            <div className="size-9 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs shrink-0 border border-primary/20">
              {userInitials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold truncate text-foreground">
                {displayName}
              </p>
              <p className="text-[11px] text-muted-foreground truncate">
                {displayEmail}
              </p>
            </div>
          </div>

          <div className="my-1.5 border-t border-border" />

          {/* Menu Options */}
          <div className="space-y-0.5">
            <button
              type="button"
              onClick={() => setUserMenuOpen(false)}
              className="w-full flex items-center gap-2.5 px-2.5 py-1.5 text-xs rounded-md text-foreground hover:bg-accent transition-colors"
            >
              <Settings className="size-3.5 text-muted-foreground" />
              <span>Account Settings</span>
            </button>

            {/* Quick Theme Switcher */}
            <button
              type="button"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="w-full flex items-center justify-between px-2.5 py-1.5 text-xs rounded-md text-foreground hover:bg-accent transition-colors"
            >
              <div className="flex items-center gap-2.5">
                {theme === "dark" ? (
                  <Moon className="size-3.5 text-muted-foreground" />
                ) : (
                  <Sun className="size-3.5 text-muted-foreground" />
                )}
                <span>Appearance</span>
              </div>
              <span className="text-[10px] uppercase px-1.5 py-0.5 bg-muted rounded text-muted-foreground">
                {theme}
              </span>
            </button>

            <button
              type="button"
              onClick={() => setUserMenuOpen(false)}
              className="w-full flex items-center gap-2.5 px-2.5 py-1.5 text-xs rounded-md text-foreground hover:bg-accent transition-colors"
            >
              <HelpCircle className="size-3.5 text-muted-foreground" />
              <span>Help & Support</span>
            </button>
          </div>

          <div className="my-1.5 border-t border-border" />

          {/* Logout Action */}
          <button
            type="button"
            onClick={() => {
              setUserMenuOpen(false);
              logout();
            }}
            className="w-full flex items-center gap-2.5 px-2.5 py-1.5 text-xs rounded-md text-destructive hover:bg-destructive/10 transition-colors font-medium"
          >
            <LogOut className="size-3.5" />
            <span>Log out</span>
          </button>
        </div>
      )}

      {/* User Card Trigger */}
      <button
        type="button"
        onClick={toggleUserMenu}
        className={cn(
          "w-full flex items-center gap-2.5 p-2 rounded-xl text-left transition-all",
          "hover:bg-sidebar-accent text-sidebar-foreground",
          userMenuOpen && "bg-sidebar-accent",
          isCollapsed && "justify-center p-1.5"
        )}
        title={displayName}
      >
        <div className="relative shrink-0">
          <div className="size-8 rounded-full bg-gradient-to-tr from-primary to-primary/60 text-primary-foreground flex items-center justify-center font-bold text-xs shadow-2xs">
            {userInitials}
          </div>
          {/* Status dot */}
          <span className="absolute bottom-0 right-0 size-2.5 rounded-full bg-emerald-500 ring-2 ring-sidebar" />
        </div>

        {!isCollapsed && (
          <>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold truncate leading-tight">
                {displayName}
              </p>
              <p className="text-[11px] text-muted-foreground truncate leading-tight">
                {displayEmail}
              </p>
            </div>
            <ChevronsUpDown className="size-3.5 text-muted-foreground shrink-0" />
          </>
        )}
      </button>
    </div>
  );
}

// ── Main Sidebar Orchestrator ──────────────────────────────
export function Sidebar({ className }: { className?: string } = {}) {
  const isCollapsed = useSidebarStore((state) => state.isCollapsed);
  const isMobileOpen = useSidebarStore((state) => state.isMobileOpen);
  const toggleCollapse = useSidebarStore((state) => state.toggleCollapse);
  const closeMobileSidebar = useSidebarStore((state) => state.closeMobileSidebar);

  const sidebarContent = (
    <aside
      className={cn(
        "relative flex flex-col h-full bg-sidebar border-r border-sidebar-border text-sidebar-foreground transition-all duration-300 ease-in-out select-none",
        isCollapsed ? "w-16" : "w-64 md:w-72",
        className
      )}
    >
      {/* ── 1. Header (Brand Logo & Collapse Button) ────── */}
      <SidebarHeader />

      {/* ── 2. New Chat & Search Actions ──────────── */}
      <SidebarActions />

      {/* ── 3. Categorized Chat Threads List ───────── */}
      <SidebarThreadList />

      {/* ── 4. Bottom User Profile & Popover ─────────── */}
      <SidebarUserMenu />

      {/* Collapse Expand Toggle button for collapsed desktop mode */}
      {isCollapsed && (
        <div className="p-2 border-t border-sidebar-border/40 flex justify-center hidden md:flex">
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={toggleCollapse}
            className="text-muted-foreground hover:text-foreground"
            title="Expand Sidebar"
          >
            <PanelLeft className="size-4" />
          </Button>
        </div>
      )}
    </aside>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <div className="hidden md:flex h-full shrink-0">{sidebarContent}</div>

      {/* Mobile Drawer Overlay Sidebar */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
            onClick={closeMobileSidebar}
          />
          {/* Mobile Slide-in Panel */}
          <div className="relative z-50 w-72 max-w-[85vw] h-full shadow-2xl animate-in slide-in-from-left duration-200">
            {sidebarContent}
            <button
              type="button"
              onClick={closeMobileSidebar}
              className="absolute top-3 right-3 p-1.5 rounded-full bg-sidebar-accent text-sidebar-foreground hover:bg-muted"
            >
              <X className="size-4" />
            </button>
          </div>
        </div>
      )}
    </>
  );
}

// ── Mobile Sidebar Trigger Button ──────────────────────────
export function MobileSidebarTrigger({ className }: { className?: string } = {}) {
  const openMobileSidebar = useSidebarStore((state) => state.openMobileSidebar);

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      onClick={openMobileSidebar}
      className={cn("md:hidden text-muted-foreground hover:text-foreground", className)}
      title="Open Sidebar"
    >
      <Menu className="size-5" />
    </Button>
  );
}
