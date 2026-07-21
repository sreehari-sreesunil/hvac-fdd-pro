"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/AuthProvider";
import { useRequireAuth } from "@/lib/auth/useRequireAuth";
import { WizardShell } from "@/components/onboarding/WizardShell";
import { StepCreateOrg } from "@/components/onboarding/StepCreateOrg";
import { StepCreateFacility } from "@/components/onboarding/StepCreateFacility";
import { StepCreateAsset } from "@/components/onboarding/StepCreateAsset";

const STEPS = ["Organization", "Facility", "Asset"];

export default function OnboardingPage() {
  const status = useRequireAuth();
  const { currentOrgId } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [facilityId, setFacilityId] = useState<string | null>(null);

  if (status !== "authenticated") {
    return <p className="text-center text-sm text-text-muted">Loading…</p>;
  }

  return (
    <WizardShell steps={STEPS} currentStep={step}>
      {step === 0 && <StepCreateOrg onDone={() => setStep(1)} />}
      {step === 1 && currentOrgId && (
        <StepCreateFacility
          organizationId={currentOrgId}
          onDone={(id) => {
            setFacilityId(id);
            setStep(2);
          }}
        />
      )}
      {step === 2 && facilityId && (
        <StepCreateAsset facilityId={facilityId} onDone={() => router.push("/dashboard")} />
      )}
    </WizardShell>
  );
}
