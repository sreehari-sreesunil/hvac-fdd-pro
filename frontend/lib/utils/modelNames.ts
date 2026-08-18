/**
 * Maps internal model names (e.g. "simulated_condenser_fouling") to
 * clean, user-facing display names ("Condenser Fouling").
 *
 * The "simulated_"/"experimental_" prefix is a real, meaningful internal
 * distinction (which training data source each model came from - physics
 * simulation vs. a real physical test rig), but it's an ML-engineering
 * detail, not something a facilities manager using the product needs to
 * see. The real model_name is still used for every actual API call
 * (predictions, attribution, explanation) - this is presentation-only,
 * not a backend rename.
 */

const MODEL_DISPLAY_NAMES: Record<string, string> = {
  simulated_condenser_fouling: "Condenser Fouling",
  simulated_evaporator_fouling: "Evaporator Fouling",
  simulated_overcharge: "Refrigerant Overcharge",
  simulated_liquidline_restriction: "Liquid Line Restriction",
  simulated_suctionline_restriction: "Suction Line Restriction",
  simulated_anomaly_gatekeeper: "Anomaly Detection",
  experimental_oa_damper_stuck: "Outdoor Air Damper Stuck",
  experimental_econ_setpoint_too_low: "Economizer Setpoint Too Low",
};

/**
 * Returns a clean display name for a model. Falls back to a generic
 * title-cased version of the raw name (splitting on underscores) for
 * any model not in the explicit map above - so a newly trained model
 * added later doesn't show as a completely raw, unmapped string before
 * someone remembers to add it here.
 */
export function getModelDisplayName(modelName: string): string {
  if (modelName in MODEL_DISPLAY_NAMES) {
    return MODEL_DISPLAY_NAMES[modelName];
  }
  return modelName
    .replace(/^(simulated_|experimental_)/, "")
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
