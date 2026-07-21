import { ApiError, normalizeErrorResponse } from "./utils/errors";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  notifyAuthExpired,
  setTokens,
} from "./auth/token-store";
import type { TokenPair } from "./api-types";

export type Service = "auth" | "asset" | "telemetry";

const BASE_URLS: Record<Service, string> = {
  auth: process.env.NEXT_PUBLIC_AUTH_SERVICE_URL ?? "http://localhost:8000",
  asset: process.env.NEXT_PUBLIC_ASSET_SERVICE_URL ?? "http://localhost:8001",
  telemetry: process.env.NEXT_PUBLIC_TELEMETRY_SERVICE_URL ?? "http://localhost:8002",
};

type ApiFetchOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  /** Attach the Authorization header and participate in 401 refresh. Default true. */
  auth?: boolean;
};

let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const response = await fetch(`${BASE_URLS.auth}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!response.ok) return false;
        const pair = (await response.json()) as TokenPair;
        setTokens({ accessToken: pair.access_token, refreshToken: pair.refresh_token });
        return true;
      } catch {
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

async function rawFetch(
  service: Service,
  path: string,
  opts: ApiFetchOptions,
): Promise<Response> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (opts.auth !== false) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  return fetch(`${BASE_URLS[service]}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
}

export async function apiFetch<T>(
  service: Service,
  path: string,
  opts: ApiFetchOptions = {},
): Promise<T> {
  let response: Response;
  try {
    response = await rawFetch(service, path, opts);
  } catch {
    // fetch() itself threw (DNS failure, connection refused, offline) —
    // there's no Response to normalize, so treat it the same as a 503:
    // the service is unreachable, not "some unknown client-side bug".
    throw new ApiError(0, "unavailable", "Could not reach the service.");
  }

  if (response.status === 401 && opts.auth !== false) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      try {
        response = await rawFetch(service, path, opts);
      } catch {
        throw new ApiError(0, "unavailable", "Could not reach the service.");
      }
    } else {
      clearTokens();
      notifyAuthExpired();
      throw await normalizeErrorResponse(response);
    }
  }

  if (!response.ok) {
    throw await normalizeErrorResponse(response);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export { ApiError };
