# OpenRHTV Cascade — frontend (W5D2 deploy)
#
# Stage 1: npm build → static dist/
# Stage 2: nginx 反代 + 静态托管
#
# Two upstream routes nginx proxies through:
#   /api/*  →  backend:8766  (HTTP)
#   /ws     →  backend:8765  (WebSocket)
# Everything else: serve dist/ static + SPA fallback to index.html

FROM node:20-alpine AS builder
WORKDIR /app

# package-lock cache layer
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . ./
# legal docs copy is a predev/prebuild hook — make sure they're in place
RUN npm run copy-legal && npm run build

# ---

FROM nginx:1.27-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost/ > /dev/null || exit 1
