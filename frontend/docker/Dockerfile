# =============================================================================
# Frontend — Next.js (standalone output)
#
# Build context: frontend/
# Multi-stage build: deps → builder → runner
#
# Produces a minimal standalone Node.js server (~50 MB) with all pages
# pre-rendered. NEXT_PUBLIC_API_URL is baked in at build time (it runs in the
# browser, so it must be known during `next build`).
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

# API URL is a build arg because NEXT_PUBLIC_* vars are inlined into the
# client JS bundle during `next build`. Override for each environment:
#   docker build --build-arg NEXT_PUBLIC_API_URL=https://api.prod.example.com ...
ARG NEXT_PUBLIC_API_URL=http://localhost:18080/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

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
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000

CMD ["node", "server.js"]
