import { ForcedTheme } from "@/lib/theme/ThemeProvider";
import { MarketingNav, MarketingFooter } from "@/components/layout/MarketingNav";

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <ForcedTheme theme="dark">
      <div className="flex min-h-full flex-1 flex-col bg-bg text-text-primary">
        <MarketingNav />
        <main className="flex-1">{children}</main>
        <MarketingFooter />
      </div>
    </ForcedTheme>
  );
}
