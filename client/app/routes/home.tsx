import { useAuthStore } from "@/lib/ZustandStore";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LogOut, User as UserIcon } from "lucide-react";

export default function HomePage() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  return (
    <div className="min-h-screen bg-background p-6">
      <header className="flex justify-between items-center pb-6 border-b border-border">
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <div className="flex items-center gap-4">
          <ThemeToggle />
          <Button variant="outline" size="sm" onClick={logout} className="gap-2">
            <LogOut className="h-4 w-4" />
            Logout
          </Button>
        </div>
      </header>
      <main className="mt-8 max-w-xl mx-auto space-y-4">
        <div className="p-6 rounded-lg border border-border bg-card shadow-sm space-y-3">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-primary/10 rounded-full text-primary">
              <UserIcon className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Logged in as</p>
              <p className="text-lg font-semibold">{user?.username || "Authenticated User"}</p>
            </div>
          </div>
          {user?.email && (
            <p className="text-sm text-muted-foreground">
              Email: <span className="font-medium text-foreground">{user.email}</span>
            </p>
          )}
        </div>
      </main>
    </div>
  );
}