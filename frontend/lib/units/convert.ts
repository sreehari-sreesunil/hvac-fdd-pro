export type UnitSystem = "imperial" | "metric";

const FAHRENHEIT_ALIASES = new Set(["f", "°f", "degf", "fahrenheit"]);
const CELSIUS_ALIASES = new Set(["c", "°c", "degc", "celsius"]);

export type RecognizedTempUnit = "F" | "C";

/** Best-effort recognizer for the free-text MetricDefinition.unit field. */
export function recognizeTempUnit(unit: string | null | undefined): RecognizedTempUnit | null {
  if (!unit) return null;
  const normalized = unit.trim().toLowerCase();
  if (FAHRENHEIT_ALIASES.has(normalized)) return "F";
  if (CELSIUS_ALIASES.has(normalized)) return "C";
  return null;
}

export function fahrenheitToCelsius(value: number): number {
  return ((value - 32) * 5) / 9;
}

export function celsiusToFahrenheit(value: number): number {
  return (value * 9) / 5 + 32;
}

/**
 * Converts a raw reading to the display unit implied by `system`, when the
 * source unit is a recognized temperature unit. Returns the original value
 * and unit unconverted when the unit string isn't recognized, rather than
 * guessing.
 */
export function convertForDisplay(
  value: number,
  sourceUnit: string | null | undefined,
  system: UnitSystem,
): { value: number; unit: string } {
  const recognized = recognizeTempUnit(sourceUnit);
  if (!recognized) {
    return { value, unit: sourceUnit ?? "" };
  }
  const targetUnit: RecognizedTempUnit = system === "imperial" ? "F" : "C";
  if (recognized === targetUnit) {
    return { value, unit: `°${targetUnit}` };
  }
  const converted =
    recognized === "F" ? fahrenheitToCelsius(value) : celsiusToFahrenheit(value);
  return { value: converted, unit: `°${targetUnit}` };
}
