"use client";

import { useState } from "react";
import { Sun, Moon, AlertTriangle } from "lucide-react";
import { useTheme } from "@/lib/theme/ThemeProvider";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { FormField, Input, Select } from "@/components/ui/FormField";
import { cn } from "@/lib/utils/cn";

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-border py-10 first:border-t-0 first:pt-0">
      <h2 className="mb-6 font-mono text-xs font-medium uppercase tracking-widest text-text-muted">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Swatch({ name, className }: { name: string; className: string }) {
  return (
    <div className="flex flex-col gap-2">
      <div className={cn("h-16 w-full rounded-surface", className)} />
      <span className="font-mono text-xs text-text-muted">{name}</span>
    </div>
  );
}

export default function DesignSystemPage() {
  const { theme, toggleTheme } = useTheme();
  const [selectValue, setSelectValue] = useState("");

  return (
    <div className="mx-auto max-w-5xl px-6 py-12">
      <header className="mb-12 flex items-start justify-between gap-4 border-b-2 border-text-primary pb-6">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-text-muted">
            #00 — DESIGN SYSTEM
          </p>
          <h1 className="font-display text-4xl font-bold leading-none text-text-primary">
            Plenum Control
          </h1>
          <p className="mt-2 max-w-lg text-sm text-text-muted">
            Brutalist structure, neomorphic surfaces. Review scaffold only —
            not linked from app navigation.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={toggleTheme}>
          {theme === "light" ? <Moon size={14} /> : <Sun size={14} />}
          {theme === "light" ? "Dark" : "Light"}
        </Button>
      </header>

      <Section title="01 — Color">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Swatch name="bg" className="border border-border bg-bg" />
          <Swatch name="surface" className="border border-border bg-surface" />
          <Swatch name="elevated" className="border border-border bg-elevated" />
          <Swatch name="neo-base" className="bg-neo-base shadow-neo-resting" />
          <Swatch name="accent-brand" className="bg-accent-brand" />
          <Swatch name="accent-primary (status)" className="bg-accent-primary" />
          <Swatch name="accent-warning (status)" className="bg-accent-warning" />
          <Swatch name="accent-critical (status)" className="bg-accent-critical" />
        </div>
      </Section>

      <Section title="02 — Typography">
        <div className="flex flex-col gap-4">
          <p className="font-display text-4xl font-bold leading-none text-text-primary">
            Fault Detection
          </p>
          <p className="font-display text-3xl font-semibold text-text-primary">
            Diagnostics Console
          </p>
          <p className="font-display text-2xl font-semibold text-text-primary">
            Asset Health Overview
          </p>
          <p className="text-base text-text-primary">
            Body text in Inter — legible at small sizes for a data-dense
            operational dashboard. The quick brown fox jumps over the lazy
            dog.
          </p>
          <p className="font-mono text-xs uppercase tracking-widest text-text-muted">
            MONO LABEL — RTU-04 · SENSOR_ID: 88213 · 2026-08-12T09:41:02Z
          </p>
        </div>
      </Section>

      <Section title="03 — Shadow presets">
        <div className="grid grid-cols-3 gap-4">
          <div className="flex h-24 items-center justify-center rounded-surface bg-neo-base text-xs text-text-muted shadow-neo-resting">
            resting
          </div>
          <div className="flex h-24 items-center justify-center rounded-surface bg-neo-base text-xs text-text-muted shadow-neo-active">
            active / pressed
          </div>
          <div className="flex h-24 items-center justify-center rounded-surface bg-neo-base text-xs text-text-muted opacity-70 shadow-neo-disabled">
            disabled
          </div>
        </div>
      </Section>

      <Section title="04 — Button">
        <div className="flex flex-wrap items-center gap-4">
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
          <Button variant="primary" size="sm">
            Small
          </Button>
          <Button variant="primary" disabled>
            Disabled
          </Button>
        </div>
      </Section>

      <Section title="05 — Card">
        <div className="grid grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle>RTU-04</CardTitle>
              <Badge tone="warning" icon={AlertTriangle}>
                Fault
              </Badge>
            </CardHeader>
            <p className="text-sm text-text-muted">
              Supply air temperature drifting above setpoint for 3 cycles.
            </p>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>AHU-01</CardTitle>
              <Badge tone="primary">Nominal</Badge>
            </CardHeader>
            <p className="text-sm text-text-muted">
              All monitored points within expected range.
            </p>
          </Card>
        </div>
      </Section>

      <Section title="06 — Input / Select">
        <div className="grid grid-cols-2 gap-4">
          <FormField label="Facility name" htmlFor="ds-facility">
            <Input id="ds-facility" placeholder="North Campus Plant" />
          </FormField>
          <FormField label="Ingestion key" htmlFor="ds-key" error="Key already revoked">
            <Input id="ds-key" aria-invalid defaultValue="ik_live_••••" />
          </FormField>
          <FormField label="Asset type" htmlFor="ds-asset-type">
            <Select
              id="ds-asset-type"
              value={selectValue}
              onChange={(e) => setSelectValue(e.target.value)}
            >
              <option value="">Select…</option>
              <option value="rtu">Rooftop unit</option>
              <option value="ahu">Air handling unit</option>
            </Select>
          </FormField>
        </div>
      </Section>

      <Section title="07 — Badge">
        <div className="flex flex-wrap gap-3">
          <Badge tone="neutral">Neutral</Badge>
          <Badge tone="primary">Primary</Badge>
          <Badge tone="warning" icon={AlertTriangle}>
            Warning
          </Badge>
          <Badge tone="critical" icon={AlertTriangle}>
            Critical
          </Badge>
        </div>
      </Section>
    </div>
  );
}
