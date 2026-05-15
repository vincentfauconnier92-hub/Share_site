# ── Stage 1 : installation des dépendances ────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --frozen-lockfile

# ── Stage 2 : build de production ─────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ── Stage 3 : image finale allégée ────────────────────────────────────
FROM node:20-alpine
WORKDIR /app

# Utilisateur non-root (uid 1001)
RUN addgroup -g 1001 nextjs \
    && adduser -u 1001 -G nextjs -s /bin/sh -D nextjs

# Seuls les artefacts de build sont copiés (pas node_modules, pas sources)
COPY --from=builder --chown=nextjs:nextjs /app/public ./public
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

USER nextjs

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

EXPOSE 3000
CMD ["node", "server.js"]
