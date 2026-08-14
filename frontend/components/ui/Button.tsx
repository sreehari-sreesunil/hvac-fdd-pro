import { forwardRef } from "react";
import { cn } from "@/lib/utils/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
};

/* Ice Mint / rose fills are light, pastel hues — white text on top of them
   fails AA. Both light-fill variants use --ink-on-accent (a fixed dark
   ink) instead. */
const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    "bg-accent-brand text-ink-on-accent hover:brightness-110 active:brightness-95 disabled:bg-neo-base disabled:text-text-muted",
  secondary:
    "bg-neo-base text-text-primary hover:text-accent-brand-ink disabled:text-text-muted",
  ghost:
    "bg-transparent text-text-primary shadow-none hover:bg-neo-base hover:shadow-neo-resting disabled:text-text-muted",
  danger:
    "bg-accent-critical text-ink-on-accent hover:brightness-110 active:brightness-95 disabled:bg-neo-base disabled:text-text-muted",
};

const SIZE_CLASSES: Record<Size, string> = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 text-sm",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-surface font-medium",
          "shadow-neo-resting transition-[filter,box-shadow] active:shadow-neo-active",
          "disabled:cursor-not-allowed disabled:shadow-neo-disabled disabled:opacity-70",
          VARIANT_CLASSES[variant],
          SIZE_CLASSES[size],
          className,
        )}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";
