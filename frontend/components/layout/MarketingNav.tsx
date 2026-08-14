import Link from "next/link";
import { Button } from "@/components/ui/Button";

export function MarketingNav() {
  return (
    <header className="flex h-16 items-center justify-between border-b-2 border-text-primary px-6">
      <Link href="/" className="font-display text-lg font-bold text-text-primary">
        HVAC-FDD Pro
      </Link>
      <div className="flex items-center gap-2">
        <Link href="/login">
          <Button variant="ghost" size="sm">
            Log in
          </Button>
        </Link>
        <Link href="/signup">
          <Button size="sm">Sign up</Button>
        </Link>
      </div>
    </header>
  );
}

export function MarketingFooter() {
  return (
    <footer className="border-t-2 border-text-primary px-6 py-8">
      <p className="font-mono text-xs uppercase tracking-widest text-text-muted">
        HVAC-FDD Pro — fault detection and diagnostics for commercial HVAC.
      </p>
    </footer>
  );
}
