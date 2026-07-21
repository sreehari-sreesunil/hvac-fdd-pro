"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Bot, Building2, ChevronDown, ChevronRight, Cpu, LayoutGrid, Settings } from "lucide-react";
import { useAuth } from "@/lib/auth/AuthProvider";
import { listFacilities } from "@/lib/api/assets";
import { listAssets } from "@/lib/api/assets";
import { qk } from "@/lib/query/keys";
import { cn } from "@/lib/utils/cn";
import { Select } from "@/components/ui/FormField";

function FacilityRow({ facilityId, facilityName, expanded }: { facilityId: string; facilityName: string; expanded: boolean }) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const assetsQuery = useQuery({
    queryKey: qk.assets(facilityId),
    queryFn: () => listAssets(facilityId),
    enabled: open,
  });

  return (
    <div>
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-text-muted hover:bg-elevated hover:text-text-primary"
          aria-label={open ? `Collapse ${facilityName}` : `Expand ${facilityName}`}
        >
          {expanded ? (
            open ? (
              <ChevronDown size={14} strokeWidth={1.75} />
            ) : (
              <ChevronRight size={14} strokeWidth={1.75} />
            )
          ) : (
            <Building2 size={16} strokeWidth={1.75} />
          )}
        </button>
        <Link
          href={`/facilities/${facilityId}`}
          className={cn(
            "flex-1 truncate rounded-md px-2 py-1.5 text-sm hover:bg-elevated",
            pathname === `/facilities/${facilityId}` && "bg-elevated font-medium text-accent-primary-ink",
            !expanded && "sr-only",
          )}
        >
          {facilityName}
        </Link>
      </div>
      {expanded && open && (
        <div className="ml-8 flex flex-col gap-0.5 border-l border-border pl-2">
          {assetsQuery.isLoading && (
            <span className="py-1 text-xs text-text-muted">Loading…</span>
          )}
          {assetsQuery.data?.length === 0 && (
            <span className="py-1 text-xs text-text-muted">No assets yet</span>
          )}
          {assetsQuery.data?.map((asset) => (
            <Link
              key={asset.id}
              href={`/facilities/${facilityId}/assets/${asset.id}`}
              className={cn(
                "flex items-center gap-1.5 truncate rounded-md px-2 py-1 text-sm text-text-muted hover:bg-elevated hover:text-text-primary",
                pathname === `/facilities/${facilityId}/assets/${asset.id}` &&
                  "bg-elevated font-medium text-accent-primary-ink",
              )}
            >
              <Cpu size={12} strokeWidth={1.75} className="shrink-0" />
              <span className="truncate font-mono-num text-xs">{asset.name}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function Sidebar({ expanded }: { expanded: boolean }) {
  const { organizations, currentOrgId, setCurrentOrgId } = useAuth();
  const pathname = usePathname();

  const facilitiesQuery = useQuery({
    queryKey: qk.facilities(currentOrgId ?? ""),
    queryFn: () => listFacilities(currentOrgId as string),
    enabled: !!currentOrgId,
  });

  const navLinks = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutGrid },
    { href: "/facilities", label: "Facilities", icon: Building2 },
    { href: "/copilot", label: "AI Copilot", icon: Bot },
    { href: "/settings", label: "Settings", icon: Settings },
  ];

  return (
    <nav className="flex h-full flex-col gap-4 overflow-y-auto p-3" aria-label="Primary">
      {expanded && organizations.length > 0 && (
        <Select
          aria-label="Current organization"
          value={currentOrgId ?? ""}
          onChange={(e) => setCurrentOrgId(e.target.value)}
          className="w-full"
        >
          {organizations.map((org) => (
            <option key={org.id} value={org.id}>
              {org.name}
            </option>
          ))}
        </Select>
      )}

      <div className="flex flex-col gap-0.5">
        {navLinks.map((link) => {
          const Icon = link.icon;
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-2 py-2 text-sm font-medium text-text-muted hover:bg-elevated hover:text-text-primary",
                active && "bg-elevated text-accent-primary-ink",
                !expanded && "justify-center",
              )}
              title={link.label}
            >
              <Icon size={18} strokeWidth={1.75} className="shrink-0" />
              {expanded && <span>{link.label}</span>}
            </Link>
          );
        })}
      </div>

      {expanded && <div className="my-1 h-px bg-border" />}

      <div className="flex flex-col gap-0.5">
        {expanded && (
          <p className="px-2 text-xs font-medium uppercase tracking-wide text-text-muted">
            Facilities
          </p>
        )}
        {facilitiesQuery.isLoading && <span className="px-2 text-xs text-text-muted">Loading…</span>}
        {facilitiesQuery.data?.map((facility) => (
          <FacilityRow
            key={facility.id}
            facilityId={facility.id}
            facilityName={facility.name}
            expanded={expanded}
          />
        ))}
      </div>
    </nav>
  );
}
