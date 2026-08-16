"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import * as authApi from "@/lib/api/auth";
import {
  clearTokens,
  getAccessToken,
  registerAuthExpiredHandler,
  setTokens,
} from "./token-store";
import type { OrganizationOut, Role, UserOut } from "@/lib/api-types";

type AuthContextValue = {
  /** Undetermined while the initial token/org hydration is in flight. */
  status: "loading" | "authenticated" | "unauthenticated";
  organizations: OrganizationOut[];
  currentOrgId: string | null;
  setCurrentOrgId: (orgId: string) => void;
  currentOrgRole: Role | null;
  hasRole: (roles: Role[]) => boolean;
  signup: (body: { email: string; password: string; full_name?: string }) => Promise<UserOut>;
  login: (body: { email: string; password: string }) => Promise<void>;
  logout: () => void;
  refetchOrganizations: () => Promise<void>;
  createOrganization: (body: { name: string }) => Promise<OrganizationOut>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [status, setStatus] = useState<AuthContextValue["status"]>("loading");
  const [organizations, setOrganizations] = useState<OrganizationOut[]>([]);
  const [currentOrgId, setCurrentOrgIdState] = useState<string | null>(null);

  const loadOrganizations = useCallback(async () => {
    const orgs = await authApi.listOrganizations();
    setOrganizations(orgs);
    setCurrentOrgIdState((prev) => prev ?? orgs[0]?.id ?? null);
    return orgs;
  }, []);

  useEffect(() => {
    registerAuthExpiredHandler(() => {
      setStatus("unauthenticated");
      setOrganizations([]);
      setCurrentOrgIdState(null);
      router.replace("/login");
    });
  }, [router]);

  useEffect(() => {
    let cancelled = false;
    async function hydrate() {
      const token = getAccessToken();
      if (!token) {
        setStatus("unauthenticated");
        return;
      }
      try {
        await loadOrganizations();
        if (!cancelled) setStatus("authenticated");
      } catch {
        if (!cancelled) {
          clearTokens();
          setStatus("unauthenticated");
        }
      }
    }
    hydrate();
    return () => {
      cancelled = true;
    };
  }, [loadOrganizations]);

  const signup = useCallback(
    (body: { email: string; password: string; full_name?: string }) => authApi.signup(body),
    [],
  );

  const login = useCallback(
    async (body: { email: string; password: string }) => {
      const pair = await authApi.login(body);
      setTokens({ accessToken: pair.access_token, refreshToken: pair.refresh_token });
      setCurrentOrgIdState(null);
      await loadOrganizations();
      setStatus("authenticated");
    },
    [loadOrganizations],
  );

  const logout = useCallback(() => {
    clearTokens();
    setOrganizations([]);
    setCurrentOrgIdState(null);
    setStatus("unauthenticated");
    router.replace("/login");
  }, [router]);

  const setCurrentOrgId = useCallback((orgId: string) => setCurrentOrgIdState(orgId), []);

  const createOrganization = useCallback(async (body: { name: string }) => {
    const org = await authApi.createOrganization(body);
    setOrganizations((prev) => [...prev, org]);
    setCurrentOrgIdState(org.id);
    return org;
  }, []);

  const currentOrgRole = useMemo(
    () => organizations.find((o) => o.id === currentOrgId)?.role ?? null,
    [organizations, currentOrgId],
  );

  const hasRole = useCallback(
    (roles: Role[]) => (currentOrgRole ? roles.includes(currentOrgRole) : false),
    [currentOrgRole],
  );

  const value: AuthContextValue = {
    status,
    organizations,
    currentOrgId,
    setCurrentOrgId,
    currentOrgRole,
    hasRole,
    signup,
    login,
    logout,
    refetchOrganizations: async () => {
      await loadOrganizations();
    },
    createOrganization,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
