# syntax=docker/dockerfile:1.7
# OpenRHTV Cascade — frontend (W5D2 deploy, W5D3 cache optimization)
#
# Stage 1: npm build → static dist/
# Stage 2: nginx 反代 + 静态托管
#
# IMPORTANT: build context is REPO ROOT (see docker-compose.yml), not
# ./frontend — needed so the prebuild lifecycle hook can copy
# ../docs/legal/*.md into public/legal/.
#
# Two upstream routes nginx proxies through:
#   /api/*  →  backend:8766  (HTTP)
#   /ws     →  backend:8765  (WebSocket)
# Everything else: serve dist/ static + SPA fallback to index.html

FROM node:20-alpine AS builder
WORKDIR /app

# legal docs sit at <root>/docs/legal — the frontend prebuild script
# (`cp ../docs/legal/*.md public/legal/`) reaches for them with a
# parent-dir hop, so we mirror the repo layout under /app.
COPY docs/legal /app/docs/legal

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
# W5D3 — npm cache mount: keeps node_modules tarballs cached between builds,
# so package-lock change only re-downloads incremental deltas.
# 淘宝 mirror(registry.npmmirror.com)是阿里运维的官方 npm 镜像,跟腾讯云同
# 网络区,首次 npm ci 也快。海外 CI 用 --build-arg NPM_REGISTRY= 覆盖回空。
ARG NPM_REGISTRY=https://registry.npmmirror.com
RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund --registry=${NPM_REGISTRY}

COPY frontend/ ./
# 改写解封(2026-06-01):Vite 构建期把 VITE_REWRITE_ENABLED 烤进 bundle
# (import.meta.env.VITE_REWRITE_ENABLED;rewriteAccess.resolveRewriteEnabled 读它)。
# 全量开 = "true";一键关回 = 改 build-arg 为 "false" 重建。默认 false(安全)。
ARG VITE_REWRITE_ENABLED=false
ENV VITE_REWRITE_ENABLED=${VITE_REWRITE_ENABLED}
# Pro 画布(tldraw)在 prod 域名需 licenseKey,否则画布被 tl-license-expired 挡住(localhost 豁免)。
# 注册 tldraw.dev 拿 key(免费带水印 / 付费去水印)→ 设到 prod .env 重建。空 = 不传(本地够用)。
ARG VITE_TLDRAW_LICENSE_KEY=
ENV VITE_TLDRAW_LICENSE_KEY=${VITE_TLDRAW_LICENSE_KEY}
RUN npm run build

# ---

FROM nginx:1.27-alpine AS runtime
COPY --from=builder /app/frontend/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1/ > /dev/null || exit 1
