"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { inviteToOrganization, listMembers } from "@/lib/api/auth";
import { qk } from "@/lib/query/keys";
import { ApiError } from "@/lib/api-client";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { FormField, Input, Select } from "@/components/ui/FormField";
import { Skeleton } from "@/components/ui/Skeleton";
import { QueryErrorState } from "@/components/ui/QueryErrorState";
import { useToast } from "@/components/ui/Toast";
import type { Role } from "@/lib/api-types";

const ROLES: Role[] = ["admin", "operator", "viewer"];

export function MembersCard({
  organizationId,
  isAdmin,
}: {
  organizationId: string;
  /** UI-level hiding only — the real boundary is the backend's
   *  require_role(Role.admin) on POST /organizations/{org_id}/invite.
   *  This just keeps a non-admin from seeing a form that would 403. */
  isAdmin: boolean;
}) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [error, setError] = useState<string | null>(null);

  const membersQuery = useQuery({
    queryKey: qk.members(organizationId),
    queryFn: () => listMembers(organizationId),
  });

  const inviteMutation = useMutation({
    mutationFn: () => inviteToOrganization(organizationId, { email, role }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: qk.members(organizationId) });
      showToast(`${email} added as ${role}`);
      setEmail("");
      setRole("viewer");
      setError(null);
    },
    onError: (err) => {
      // auth-service returns 404 when no account exists for that email yet
      // (there's no "invite someone with no account" email-link flow — a
      // separate, not-yet-built feature) and 400 when they're already a
      // member — both need a clearer message than the raw backend detail.
      if (err instanceof ApiError && err.status === 404) {
        setError("No account found for this email — they need to sign up first.");
      } else if (err instanceof ApiError && err.status === 400) {
        setError("Already a member.");
      } else {
        setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
      }
    },
  });

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!email.trim()) return;
    inviteMutation.mutate();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Members</CardTitle>
      </CardHeader>

      {membersQuery.isError && (
        <QueryErrorState
          error={membersQuery.error}
          onRetry={() => membersQuery.refetch()}
          resourceLabel="this organization's members"
        />
      )}

      {!membersQuery.isError && membersQuery.isLoading && (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      )}

      {!membersQuery.isError && !membersQuery.isLoading && (
        <ul className="flex flex-col">
          {membersQuery.data?.map((member) => (
            <li
              key={member.user_id}
              className="flex items-center justify-between border-b border-border py-2.5 text-sm last:border-b-0"
            >
              <span className="text-text-primary">{member.email}</span>
              <Badge tone="neutral">{member.role}</Badge>
            </li>
          ))}
        </ul>
      )}

      {isAdmin ? (
        <form
          onSubmit={onSubmit}
          className="mt-4 flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:items-end"
        >
          <div className="flex-1">
            <FormField label="Email" htmlFor="invite-email">
              <Input
                id="invite-email"
                type="email"
                required
                placeholder="teammate@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </FormField>
          </div>
          <div>
            <FormField label="Role" htmlFor="invite-role">
              <Select
                id="invite-role"
                value={role}
                onChange={(e) => setRole(e.target.value as Role)}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </Select>
            </FormField>
          </div>
          <Button type="submit" size="sm" disabled={inviteMutation.isPending}>
            <UserPlus size={14} strokeWidth={1.75} />
            {inviteMutation.isPending ? "Inviting…" : "Invite"}
          </Button>
        </form>
      ) : (
        <p className="mt-3 text-xs text-text-muted">
          Only organization admins can invite teammates.
        </p>
      )}

      {error && <p className="mt-2 text-sm text-accent-critical-ink">{error}</p>}
    </Card>
  );
}
