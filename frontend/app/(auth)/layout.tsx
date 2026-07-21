import { ForcedTheme } from "@/lib/theme/ThemeProvider";
import { SchematicBackground } from "@/components/layout/SchematicBackground";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <ForcedTheme theme="dark">
      <div className="relative flex flex-1 items-center justify-center overflow-hidden bg-bg px-4 py-12 text-text-primary">
        <SchematicBackground className="absolute inset-0 h-full w-full text-accent-primary/10" />
        <div className="relative z-10 w-full max-w-md">{children}</div>
      </div>
    </ForcedTheme>
  );
}
