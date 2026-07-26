import { useState } from "react";
import { useParams } from "react-router";
import { Sidebar, MobileSidebarTrigger, MOCK_CHAT_THREADS } from "@/components/sidebar";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Bot, User as UserIcon, Send, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ChatPage() {
  const { thread_id } = useParams<{ thread_id: string }>();
  const [mobileOpen, setMobileOpen] = useState(false);

  const activeThread = MOCK_CHAT_THREADS.find((t) => t.id === thread_id);
  const title = activeThread ? activeThread.title : `Chat (${thread_id})`;

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden">
      {/* Mounted Sidebar with active thread route */}
      <Sidebar
        isMobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      {/* Main Chat Interface */}
      <div className="flex-1 flex flex-col min-w-0 h-full">
        {/* Header */}
        <header className="h-14 border-b border-border flex items-center justify-between px-4 shrink-0 bg-background/80 backdrop-blur-xs">
          <div className="flex items-center gap-2 min-w-0">
            <MobileSidebarTrigger onClick={() => setMobileOpen(true)} />
            <h1 className="text-sm font-semibold text-foreground truncate flex items-center gap-2">
              <Sparkles className="size-4 text-primary shrink-0" />
              <span className="truncate">{title}</span>
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
          </div>
        </header>

        {/* Chat Messages Log */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
          <div className="max-w-3xl mx-auto space-y-4">
            {/* User message prompt demo */}
            <div className="flex items-start gap-3 flex-row-reverse">
              <div className="size-8 rounded-full bg-primary/20 text-primary flex items-center justify-center text-xs font-bold shrink-0">
                U
              </div>
              <div className="bg-primary text-primary-foreground p-3.5 rounded-2xl rounded-tr-xs text-sm max-w-lg shadow-2xs">
                How do I implement responsive sidebars in React Router v7 with Shadcn UI?
              </div>
            </div>

            {/* AI Assistant response demo */}
            <div className="flex items-start gap-3">
              <div className="size-8 rounded-full bg-sidebar-border text-foreground flex items-center justify-center text-xs font-bold shrink-0 border border-border">
                <Bot className="size-4" />
              </div>
              <div className="bg-card border border-border p-4 rounded-2xl rounded-tl-xs text-sm max-w-xl text-foreground space-y-2 shadow-2xs">
                <p>
                  You can build a clean, responsive sidebar using a shared layout component or by mounting a standard <code className="bg-muted px-1 py-0.5 rounded font-mono text-xs">Sidebar</code> component with mobile overlay state.
                </p>
                <ul className="list-disc pl-4 text-xs space-y-1 text-muted-foreground">
                  <li>Use Tailwind CSS breakpoints (<code className="font-mono">hidden md:flex</code>) for desktop.</li>
                  <li>Use a sliding sheet / drawer overlay for mobile screens.</li>
                  <li>Manage collapsible states & user profile menus with clean accessibility primitives.</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Chat Input Bar */}
        <div className="p-4 border-t border-border bg-background">
          <div className="max-w-3xl mx-auto flex items-center gap-2">
            <input
              type="text"
              placeholder={`Message ${title}...`}
              className="flex-1 h-10 px-4 text-sm bg-muted/40 rounded-xl border border-border focus:outline-none focus:ring-1 focus:ring-ring text-foreground placeholder:text-muted-foreground"
            />
            <Button size="icon" className="rounded-xl">
              <Send className="size-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
