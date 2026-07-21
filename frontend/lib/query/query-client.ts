import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/utils/errors";

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        // Backend connectivity failures (service down, connection refused)
        // must resolve to a real error state, not TanStack's "paused"
        // fetchStatus (its offline-queueing heuristic) — "paused" is neither
        // isLoading nor isError, so the UI would render nothing at all.
        // This app has no offline-queueing use case, so always attempt and
        // surface failures immediately.
        networkMode: "always",
        // Only "unavailable" (503 / unreachable service) is worth retrying —
        // it's the one kind that can resolve on its own. unauthorized,
        // forbidden, not_found, and validation are deterministic; retrying
        // them just delays the error state for no benefit.
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.kind !== "unavailable") return false;
          return failureCount < 2;
        },
      },
      mutations: {
        networkMode: "always",
      },
    },
  });
}
