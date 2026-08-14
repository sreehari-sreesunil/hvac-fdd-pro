"use client";

import { Menu, LogOut, Sun, Moon } from "lucide-react";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useTheme } from "@/lib/theme/ThemeProvider";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";

export function TopBar({ onMenuClick }: { onMenuClick: () => void }) {
  const { logout, currentOrgRole } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b-2 border-border bg-surface px-4">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          className="flex h-9 w-9 items-center justify-center rounded-surface text-text-muted hover:bg-neo-base md:hidden"
          aria-label="Open navigation"
        >
          <Menu size={18} strokeWidth={1.75} />
        </button>
        <span className="font-display text-sm font-semibold text-text-primary">
          HVAC-FDD Pro
        </span>
        {currentOrgRole && <Badge tone="neutral">{currentOrgRole}</Badge>}
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={toggleTheme}
          aria-label={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
          className="flex h-9 w-9 items-center justify-center rounded-surface text-text-muted hover:bg-neo-base hover:text-text-primary"
        >
          {theme === "light" ? (
            <Moon size={18} strokeWidth={1.75} />
          ) : (
            <Sun size={18} strokeWidth={1.75} />
          )}
        </button>
        <Button variant="ghost" size="sm" onClick={logout}>
          <LogOut size={14} strokeWidth={1.75} />
          Log out
        </Button>
      </div>
    </header>
  );
}
