import { Check } from "lucide-react";
import { cn } from "@/lib/utils/cn";

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
    <div className="rounded-xl border border-border bg-surface p-8">
      <ol className="mb-8 flex items-center gap-2">
        {steps.map((step, i) => {
          const done = i < currentStep;
          const active = i === currentStep;
          return (
            <li key={step} className="flex flex-1 items-center gap-2">
              <div
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-medium",
                  done && "border-accent-primary bg-accent-primary text-[#04231f]",
                  active && !done && "border-accent-primary text-accent-primary",
                  !active && !done && "border-border text-text-muted",
                )}
              >
                {done ? <Check size={14} strokeWidth={2.5} /> : i + 1}
              </div>
              <span
                className={cn(
                  "hidden text-sm sm:inline",
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
      {children}
    </div>
  );
}
