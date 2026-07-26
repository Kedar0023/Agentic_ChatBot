import { useState } from "react";
import { Sidebar, MobileSidebarTrigger } from "@/components/sidebar";
import { useAuthStore } from "@/lib/ZustandStore";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Sparkles, MessageSquarePlus, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  const user = useAuthStore((state) => state.user);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden">
      {/* Mounted Sidebar */}
      <Sidebar
        isMobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-y-auto">
        {/* Top Header Bar with Mobile Trigger & Theme Toggle */}
        <header className="h-14 border-b border-border flex items-center justify-between px-4 shrink-0 bg-background/80 backdrop-blur-xs">
          <div className="flex items-center gap-2">
            <MobileSidebarTrigger onClick={() => setMobileOpen(true)} />
            <h1 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <Sparkles className="size-4 text-primary" />
              New Conversation
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
          </div>
        </header>

        {/* Dashboard / Chat Home Content */}
        <main className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-3xl mx-auto space-y-6">
          <div className="size-16 rounded-2xl bg-primary/10 text-primary flex items-center justify-center shadow-inner">
            <Bot className="size-8" />
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground">
              What can I help you build today, {user?.username || "Friend"}?
            </h2>
            <p className="text-muted-foreground text-sm max-w-md mx-auto">
              Ask questions, analyze documents, or stream AI reasoning tokens in real-time.
            </p>
          </div>

          {/* Quick Start Action Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg text-left pt-4">
            <div className="p-4 rounded-xl border border-border bg-card hover:bg-accent/40 cursor-pointer transition-all space-y-1">
              <p className="text-xs font-semibold text-foreground">FastAPI & SSE Streaming</p>
              <p className="text-[11px] text-muted-foreground">Setup low latency async generators for chat completions.</p>
            </div>
            <div className="p-4 rounded-xl border border-border bg-card hover:bg-accent/40 cursor-pointer transition-all space-y-1">
              <p className="text-xs font-semibold text-foreground">RAG Vector Indexing</p>
              <p className="text-[11px] text-muted-foreground">Query hybrid ChromaDB & Pinecone embeddings.</p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}