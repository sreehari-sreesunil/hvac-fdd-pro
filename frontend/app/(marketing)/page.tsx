import { MarketingHero } from "@/components/marketing/MarketingHero";
import { EvalMetricsSection } from "@/components/marketing/EvalMetricsSection";
import { CopilotPreview } from "@/components/marketing/CopilotPreview";
import { CTASection } from "@/components/marketing/CTASection";

export default function MarketingHomePage() {
  return (
    <div>
      <MarketingHero />
      <EvalMetricsSection />
      <CopilotPreview />
      <CTASection />
    </div>
  );
}
