const ACCESS_KEY = "hvac_access_token";
const REFRESH_KEY = "hvac_refresh_token";

let accessToken: string | null = null;
let refreshToken: string | null = null;
let hydrated = false;

function hydrate() {
  if (hydrated || typeof window === "undefined") return;
  accessToken = window.localStorage.getItem(ACCESS_KEY);
  refreshToken = window.localStorage.getItem(REFRESH_KEY);
  hydrated = true;
}

export function getAccessToken(): string | null {
  hydrate();
  return accessToken;
}

export function getRefreshToken(): string | null {
  hydrate();
  return refreshToken;
}

export function setTokens(next: { accessToken: string; refreshToken: string }) {
  accessToken = next.accessToken;
  refreshToken = next.refreshToken;
  hydrated = true;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(ACCESS_KEY, next.accessToken);
    window.localStorage.setItem(REFRESH_KEY, next.refreshToken);
  }
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
  hydrated = true;
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(ACCESS_KEY);
    window.localStorage.removeItem(REFRESH_KEY);
  }
}

let onAuthExpired: (() => void) | null = null;

/** Registered by AuthProvider so the framework-agnostic api-client can
 *  trigger a redirect-to-login without importing Next.js router code. */
export function registerAuthExpiredHandler(handler: () => void) {
  onAuthExpired = handler;
}

export function notifyAuthExpired() {
  onAuthExpired?.();
}
