# Multi-stage build: the build stage needs the full node_modules and
# devDependencies to run `next build`, but none of that belongs in the
# final image - only .next/standalone's trimmed output does. This keeps
# the final image dramatically smaller than copying the whole project +
# full node_modules, matching the same "smaller final image" reasoning
# already used for this project's Python services (multi-stage isn't
# needed there since Poetry's runtime deps are already lean, but the
# principle is the same).

FROM node:22-slim AS build
WORKDIR /app

# Copy only dependency files first - Docker only re-runs `npm ci` when
# these change, not on every code edit, same layer-caching trick already
# used in every other service's Dockerfile.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend .
# NEXT_PUBLIC_* values are baked into the client bundle AT BUILD TIME,
# not read at runtime - real, non-obvious Next.js behavior. They're
# passed as build args here specifically so they can differ between a
# local dev build and a production build without editing source code.
ARG NEXT_PUBLIC_AUTH_SERVICE_URL
ARG NEXT_PUBLIC_ASSET_SERVICE_URL
ARG NEXT_PUBLIC_TELEMETRY_SERVICE_URL
ARG NEXT_PUBLIC_ML_SERVICE_URL
ARG NEXT_PUBLIC_NOTIFICATION_SERVICE_URL
ARG NEXT_PUBLIC_COPILOT_SERVICE_URL
RUN npm run build

FROM node:22-slim AS runtime
WORKDIR /app

# .next/standalone already contains a trimmed, self-contained node_modules
# and server.js - this is the whole point of output: "standalone" in
# next.config.ts. Static assets aren't included in standalone by default
# and must be copied separately.
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
