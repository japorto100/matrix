# frontend_merger — Bun build, Node runtime.
# Multi-stage Dockerfile, kompatibel mit docker und podman.
FROM oven/bun:1 AS builder

WORKDIR /app

# Deps zuerst fuer Layer-Caching
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

# Restlicher Source (inkl. src, public, tsconfig, next.config, biome, postcss, tailwind)
COPY . .
RUN bun run build

# Runner — Node fuer Next.js standalone server
FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3003
ENV HOSTNAME=0.0.0.0

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3003
CMD ["node", "server.js"]
