"use client";

import { useState } from "react";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const status = useRequireAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  if (status !== "authenticated") {
    return (
      <div className="flex flex-1 items-center justify-center bg-bg text-text-muted">
        Loading…
      </div>
    );
  }

  return (
    <div className="flex flex-1 bg-bg text-text-primary">
      {/* Desktop full sidebar (lg and up) */}
      <aside className="hidden w-64 shrink-0 border-r border-border bg-surface lg:block">
        <Sidebar expanded />
      </aside>

      {/* Tablet icon rail (md to lg) */}
      <aside className="hidden w-16 shrink-0 border-r border-border bg-surface md:block lg:hidden">
        <Sidebar expanded={false} />
      </aside>

      {/* Mobile drawer */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-40 flex md:hidden">
          <div
            className="fixed inset-0 bg-black/50"
            onClick={() => setMobileNavOpen(false)}
            aria-hidden
          />
          <aside className="relative z-50 h-full w-64 border-r border-border bg-surface">
            <Sidebar expanded />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onMenuClick={() => setMobileNavOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
