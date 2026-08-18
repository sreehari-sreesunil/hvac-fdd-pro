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
  // real, duplicate one.
  //
  // Real bug fixed here: the original version re-evaluated this check on
  // EVERY render, not just on arrival. StepCreateOrg's own onDone
  // callback sets currentOrgId as part of legitimately completing step 0
  // of THIS SAME wizard - which flipped the guard to true mid-flow and
  // kicked the user straight to the dashboard before they ever reached
  // Facility/Asset, since the guard couldn't distinguish "arrived already
  // onboarded" from "just onboarded one step ago as part of this exact
  // session." Found live during a full onboarding dry run.
  //
  // Fix: capture whether the user already had an org the FIRST time auth
  // resolves, once, and freeze that value - the wizard's own subsequent
  // org creation no longer retroactively triggers the redirect.
  const [hadOrgOnArrival, setHadOrgOnArrival] = useState<boolean | null>(null);
  // Setting state directly during render (not in an effect) is the
  // sanctioned React pattern for "capture this once" - it's safe because
  // the condition below stops being true the moment hadOrgOnArrival is
  // set, so it can't loop, and currentOrgId is deliberately not read
  // again after this to avoid retroactively tracking it.
  if (status === "authenticated" && hadOrgOnArrival === null) {
    setHadOrgOnArrival(!!currentOrgId);
  }

  useEffect(() => {
    if (hadOrgOnArrival === true) {
      router.replace("/dashboard");
    }
  }, [hadOrgOnArrival, router]);

  if (status !== "authenticated" || hadOrgOnArrival === null || hadOrgOnArrival === true) {
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
