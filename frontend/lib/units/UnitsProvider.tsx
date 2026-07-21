"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { convertForDisplay, type UnitSystem } from "./convert";

const STORAGE_KEY = "hvac-units";

type UnitsContextValue = {
  system: UnitSystem;
  setSystem: (system: UnitSystem) => void;
  toggleSystem: () => void;
  formatValue: (value: number, sourceUnit: string | null | undefined, digits?: number) => string;
};

const UnitsContext = createContext<UnitsContextValue | null>(null);

function readStoredSystem(): UnitSystem {
  if (typeof window === "undefined") return "imperial";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored === "metric" ? "metric" : "imperial";
}

export function UnitsProvider({ children }: { children: React.ReactNode }) {
  const [system, setSystemState] = useState<UnitSystem>(readStoredSystem);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, system);
  }, [system]);

  const setSystem = useCallback((next: UnitSystem) => setSystemState(next), []);
  const toggleSystem = useCallback(
    () => setSystemState((prev) => (prev === "imperial" ? "metric" : "imperial")),
    [],
  );

  const formatValue = useCallback(
    (value: number, sourceUnit: string | null | undefined, digits = 1) => {
      const { value: converted, unit } = convertForDisplay(value, sourceUnit, system);
      return `${converted.toFixed(digits)}${unit}`;
    },
    [system],
  );

  return (
    <UnitsContext.Provider value={{ system, setSystem, toggleSystem, formatValue }}>
      {children}
    </UnitsContext.Provider>
  );
}

export function useUnits() {
  const ctx = useContext(UnitsContext);
  if (!ctx) throw new Error("useUnits must be used within a UnitsProvider");
  return ctx;
}
