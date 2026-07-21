import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { HeroSchematic } from "@/components/marketing/HeroSchematic";
import { EvalMetricsSection } from "@/components/marketing/EvalMetricsSection";
import { CopilotPreview } from "@/components/marketing/CopilotPreview";
import { CTASection } from "@/components/marketing/CTASection";

export default function MarketingHomePage() {
  return (
    <div>
      <section className="mx-auto flex max-w-6xl flex-col-reverse items-center gap-10 px-4 py-16 lg:flex-row lg:py-24">
        <div className="flex-1">
          <h1 className="font-display text-3xl font-semibold leading-tight text-text-primary sm:text-4xl">
            Catch HVAC faults before they cost you a service call.
          </h1>
          <p className="mt-4 max-w-md text-base text-text-muted">
            Live telemetry, fleet-wide visibility, and an AI copilot that explains what&apos;s wrong
            and why — for commercial rooftop units, air handlers, and chillers.
          </p>
          <div className="mt-6 flex gap-3">
            <Link href="/signup">
              <Button>Sign up</Button>
            </Link>
            <Link href="/login">
              <Button variant="secondary">Log in</Button>
            </Link>
          </div>
        </div>
        <div className="h-64 w-full flex-1 sm:h-80 lg:h-96">
          <HeroSchematic />
        </div>
      </section>

      <EvalMetricsSection />
      <CopilotPreview />
      <CTASection />
    </div>
  );
}
