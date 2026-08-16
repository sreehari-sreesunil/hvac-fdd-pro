"use client";

import { useEffect, useState } from "react";
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

  // A user who already belongs to an org (e.g. landing back on this route
  // via the browser's back button, a stale bookmark, or manually typing
  // the URL — not through any in-app link, which never points here once
  // onboarded) must never see this wizard again: StepCreateOrg has no
  // concept of "the caller already has an org" and would happily create a
  // real, duplicate one. replace (not push) so this detour doesn't linger
  // as a back-button stop, matching how the rest of the app guards routes
  // (see useRequireAuth/AuthProvider's own redirect-on-auth-state hooks).
  const alreadyOnboarded = status === "authenticated" && !!currentOrgId;
  useEffect(() => {
    if (alreadyOnboarded) {
      router.replace("/dashboard");
    }
  }, [alreadyOnboarded, router]);

  if (status !== "authenticated" || alreadyOnboarded) {
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
      {step === 2 && facilityId && currentOrgId && (
        <StepCreateAsset
          facilityId={facilityId}
          organizationId={currentOrgId}
          onDone={() => router.push("/dashboard")}
        />
      )}
    </WizardShell>
  );
}
