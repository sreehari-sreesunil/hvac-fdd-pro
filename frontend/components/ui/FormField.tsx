import { forwardRef } from "react";
import { cn } from "@/lib/utils/cn";

export function FormField({
  label,
  htmlFor,
  error,
  children,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={htmlFor}
        className="font-mono text-xs font-medium uppercase tracking-wide text-text-muted"
      >
        {label}
      </label>
      {children}
      {error && <p className="text-xs text-accent-critical-ink">{error}</p>}
    </div>
  );
}

const FIELD_BASE =
  "h-10 rounded-surface bg-neo-base px-3 text-sm text-text-primary placeholder:text-text-muted shadow-neo-active transition-shadow disabled:cursor-not-allowed disabled:opacity-70 disabled:shadow-neo-disabled";

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, "aria-invalid": ariaInvalid, ...props }, ref) => (
    <input
      ref={ref}
      aria-invalid={ariaInvalid}
      className={cn(
        FIELD_BASE,
        ariaInvalid && "shadow-none ring-2 ring-accent-critical-ink",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export const Select = forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => (
    <select ref={ref} className={cn(FIELD_BASE, className)} {...props}>
      {children}
    </select>
  ),
);
Select.displayName = "Select";
