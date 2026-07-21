import Link from "next/link";
import { Button } from "@/components/ui/Button";

export function CTASection() {
  return (
    <section className="mx-auto max-w-2xl px-4 py-24 text-center">
      <h2 className="font-display text-2xl font-semibold text-text-primary">
        Start monitoring your fleet
      </h2>
      <p className="mt-2 text-sm text-text-muted">
        Connect your facilities and assets in a few steps.
      </p>
      <div className="mt-6 flex justify-center gap-3">
        <Link href="/signup">
          <Button>Sign up</Button>
        </Link>
        <Link href="/login">
          <Button variant="secondary">Log in</Button>
        </Link>
      </div>
    </section>
  );
}
