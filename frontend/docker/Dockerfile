# =============================================================================
# Frontend — Next.js (standalone output)
#
# Build context: frontend/
# Multi-stage build: deps -> builder -> runner
#
# Produces a minimal standalone Node.js server (~50 MB) with all pages
# pre-rendered. NEXT_PUBLIC_API_URL uses a placeholder at build time that
# is replaced at runtime by entrypoint.sh, allowing a single image to
# work in any environment.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: deps — install npm dependencies (cached independently of source)
# ---------------------------------------------------------------------------
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---------------------------------------------------------------------------
# Stage 2: builder — compile the Next.js application
# ---------------------------------------------------------------------------
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build with a known placeholder — replaced at runtime by entrypoint.sh
ENV NEXT_PUBLIC_API_URL=__NEXT_PUBLIC_API_URL_PLACEHOLDER__

RUN npm run build

# ---------------------------------------------------------------------------
# Stage 3: runner — minimal production image
# ---------------------------------------------------------------------------
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Run as non-root for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy only the standalone server output + static assets + public files
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy entrypoint script
COPY --chown=nextjs:nodejs scripts/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

USER nextjs
ENV PORT=80
EXPOSE ${PORT}

ENTRYPOINT ["./entrypoint.sh"]
