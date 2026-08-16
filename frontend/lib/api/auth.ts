import { apiFetch } from "@/lib/api-client";
import type {
  InviteResponse,
  MemberOut,
  OrganizationOut,
  Role,
  TokenPair,
  UserOut,
} from "@/lib/api-types";

export function signup(body: { email: string; password: string; full_name?: string }) {
  return apiFetch<UserOut>("auth", "/auth/signup", { method: "POST", body, auth: false });
}

export function login(body: { email: string; password: string }) {
  return apiFetch<TokenPair>("auth", "/auth/login", { method: "POST", body, auth: false });
}

export function refresh(body: { refresh_token: string }) {
  return apiFetch<TokenPair>("auth", "/auth/refresh", { method: "POST", body, auth: false });
}

export function createOrganization(body: { name: string }) {
  return apiFetch<OrganizationOut>("auth", "/organizations", { method: "POST", body });
}

export function listOrganizations() {
  return apiFetch<OrganizationOut[]>("auth", "/organizations");
}

export function inviteToOrganization(orgId: string, body: { email: string; role: Role }) {
  return apiFetch<InviteResponse>("auth", `/organizations/${orgId}/invite`, {
    method: "POST",
    body,
  });
}

export function listMembers(orgId: string) {
  return apiFetch<MemberOut[]>("auth", `/organizations/${orgId}/members`);
}
