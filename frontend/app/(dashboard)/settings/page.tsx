"use client";

import { useTheme } from "@/lib/theme/ThemeProvider";
import { useUnits } from "@/lib/units/UnitsProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Toggle } from "@/components/ui/Toggle";

export default function SettingsPage() {
  const { theme, toggleTheme } = useTheme();
  const { system, toggleSystem } = useUnits();
  const { organizations, currentOrgRole } = useAuth();

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <h1 className="font-display text-xl font-semibold text-text-primary">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
        </CardHeader>
        <div className="flex items-center justify-between py-2">
          <div>
            <p className="text-sm font-medium text-text-primary">Dark mode</p>
            <p className="text-sm text-text-muted">
              Switches the dashboard between the light and dark palettes.
            </p>
          </div>
          <Toggle
            checked={theme === "dark"}
            onChange={toggleTheme}
            label="Toggle dark mode"
          />
        </div>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Units</CardTitle>
        </CardHeader>
        <div className="flex items-center justify-between py-2">
          <div>
            <p className="text-sm font-medium text-text-primary">Metric units</p>
            <p className="text-sm text-text-muted">
              Displays temperatures in °C instead of °F.
            </p>
          </div>
          <Toggle
            checked={system === "metric"}
            onChange={toggleSystem}
            label="Toggle metric units"
          />
        </div>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Organizations</CardTitle>
        </CardHeader>
        <ul className="flex flex-col gap-2">
          {organizations.map((org) => (
            <li key={org.id} className="flex items-center justify-between py-1 text-sm">
              <span className="text-text-primary">{org.name}</span>
              <span className="rounded-full border border-border bg-elevated px-2 py-0.5 text-xs capitalize text-text-muted">
                {org.role}
              </span>
            </li>
          ))}
        </ul>
        {currentOrgRole !== "admin" && (
          <p className="mt-3 text-xs text-text-muted">
            Only organization admins can invite teammates.
          </p>
        )}
      </Card>
    </div>
  );
}
