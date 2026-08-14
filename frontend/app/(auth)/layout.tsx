import { ForcedTheme } from "@/lib/theme/ThemeProvider";
import { SchematicBackground } from "@/components/layout/SchematicBackground";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <ForcedTheme theme="dark">
      <div className="relative flex flex-1 items-center justify-center overflow-hidden bg-bg px-4 py-12 text-text-primary">
        <SchematicBackground className="absolute inset-0 h-full w-full text-accent-brand/10 motion-safe:animate-schematic-drift" />

        <p className="absolute left-6 top-6 font-mono text-xs uppercase tracking-widest text-text-subtle">
          Plenum Control
        </p>
        <p className="absolute bottom-6 right-6 hidden font-mono text-xs uppercase tracking-widest text-text-subtle sm:block">
          Fault Detection &amp; Diagnostics
        </p>

        <div className="relative z-10 w-full max-w-md motion-safe:animate-fade-up">{children}</div>
      </div>
    </ForcedTheme>
  );
}
