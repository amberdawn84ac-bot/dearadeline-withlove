FROM node:20-alpine AS base
RUN npm install -g pnpm@9
WORKDIR /app

# ── Install deps ──────────────────────────────────────────────────────────────
# Copy workspace manifests so pnpm can resolve the local @adeline/core dep
FROM base AS deps
COPY package.json pnpm-workspace.yaml ./
COPY adeline-core/package.json adeline-core/tsconfig.json ./adeline-core/
COPY adeline-ui/package.json ./adeline-ui/
RUN pnpm install --no-frozen-lockfile

# ── Build ─────────────────────────────────────────────────────────────────────
FROM base AS builder
WORKDIR /app
# Source first — node_modules copied on top so they don't conflict
COPY package.json pnpm-workspace.yaml ./
COPY adeline-core ./adeline-core
COPY adeline-ui ./adeline-ui
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/adeline-core/node_modules ./adeline-core/node_modules
COPY --from=deps /app/adeline-ui/node_modules ./adeline-ui/node_modules

# Build shared types first, then UI
RUN pnpm --filter @adeline/core build
RUN NODE_OPTIONS="--max-old-space-size=2048" pnpm --filter adeline-ui build

# ── Runtime ───────────────────────────────────────────────────────────────────
# outputFileTracingRoot=monorepo-root causes standalone to mirror the full
# repo path: standalone/adeline-ui/server.js + standalone/node_modules/
FROM node:20-alpine AS runner
ENV NODE_ENV=production
WORKDIR /app

COPY --from=builder /app/adeline-ui/.next/standalone ./
COPY --from=builder /app/adeline-ui/.next/static ./adeline-ui/.next/static
COPY --from=builder /app/adeline-ui/public ./adeline-ui/public

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

WORKDIR /app/adeline-ui
CMD ["node", "server.js"]
