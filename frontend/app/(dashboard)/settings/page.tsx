"use client";

import { useTheme } from "@/lib/theme/ThemeProvider";
import { useUnits } from "@/lib/units/UnitsProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Toggle } from "@/components/ui/Toggle";
import { Badge } from "@/components/ui/Badge";
import { MembersCard } from "@/components/settings/MembersCard";

export default function SettingsPage() {
  const { theme, toggleTheme } = useTheme();
  const { system, toggleSystem } = useUnits();
  const { organizations, currentOrgId, currentOrgRole } = useAuth();

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-8">
      <header className="border-b-2 border-text-primary pb-4">
        <p className="font-mono text-xs uppercase tracking-widest text-text-muted">
          #07 — SETTINGS
        </p>
        <h1 className="font-display text-3xl font-bold leading-none text-text-primary sm:text-4xl">
          Settings
        </h1>
      </header>

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
        <ul className="flex flex-col">
          {organizations.map((org) => (
            <li
              key={org.id}
              className="flex items-center justify-between border-b border-border py-2.5 text-sm last:border-b-0"
            >
              <span className="text-text-primary">{org.name}</span>
              <Badge tone="neutral">{org.role}</Badge>
            </li>
          ))}
        </ul>
      </Card>

      {currentOrgId && (
        <MembersCard organizationId={currentOrgId} isAdmin={currentOrgRole === "admin"} />
      )}
    </div>
  );
}
