import { Check } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { Card } from "@/components/ui/Card";

export function WizardShell({
  steps,
  currentStep,
  children,
}: {
  steps: string[];
  currentStep: number;
  children: React.ReactNode;
}) {
  return (
    <Card className="p-8">
      <p className="mb-1 font-mono text-xs uppercase tracking-widest text-text-muted">
        #00 — SETUP
      </p>
      <ol className="mb-8 flex items-center gap-2">
        {steps.map((step, i) => {
          const done = i < currentStep;
          const active = i === currentStep;
          return (
            <li key={step} className="flex flex-1 items-center gap-2">
              <div
                key={done ? "done" : "pending"}
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-medium motion-safe:animate-step-complete",
                  done && "border-accent-brand bg-accent-brand text-ink-on-accent",
                  active &&
                    !done &&
                    "border-accent-brand text-accent-brand-ink shadow-[0_0_8px_var(--accent-brand)]",
                  !active && !done && "border-border text-text-muted",
                )}
              >
                {done ? <Check size={14} strokeWidth={2.5} /> : i + 1}
              </div>
              <span
                className={cn(
                  "hidden font-mono text-xs uppercase tracking-wide sm:inline",
                  active ? "font-medium text-text-primary" : "text-text-muted",
                )}
              >
                {step}
              </span>
              {i < steps.length - 1 && <div className="h-px flex-1 bg-border" />}
            </li>
          );
        })}
      </ol>
      <div key={currentStep} className="motion-safe:animate-fade-up">
        {children}
      </div>
    </Card>
  );
}
