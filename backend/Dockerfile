# syntax=docker/dockerfile:1.7
# OpenRHTV Cascade — backend (W5D2 deploy, W5D3 cache optimization)
#
# Image: python:3.12-slim + uv + ffmpeg (yt-dlp dep)
# Entry: python -m agent.server  (WS :8765 + HTTP :8766)
# Volume: /data → SQLite + ARK cache
# Env:    see .env.example — at minimum ARK_API_KEY, INVITE_CODES,
#         CASCADE_UPSTREAM=doubao_direct, TOPRADOR_RESOLVER_MODE=douyin_share
#
# Cache strategy (W5D3):
#   1. apt cache mount    — apt-get fast on rebuild
#   2. uv cache mount     — wheels survive between builds
#   3. deps layer SPLIT   — src/ change does NOT re-download 70MB of deps,
#                           only re-installs the local `agent` package (~5s)

FROM python:3.12-slim AS builder

# uv = fastest Python package manager. We pin to a known good version.
# apt cache mount: rm of /var/lib/apt/lists is no longer needed since BuildKit
# manages it via the cache mount; we still skip recommends to keep image small.
# W5D3 — Debian apt 走 Aliyun 镜像(Tencent Cloud 同区,首次 build 也快)。
# python:3.12-slim 当前基于 Debian Trixie,sources 用 Deb822 格式
# (/etc/apt/sources.list.d/debian.sources)。老版本 Debian 用 sources.list,
# 都 sed 一遍以兼容。`|| true` 保证 sources 文件不存在时不挂。
ARG DEBIAN_MIRROR=https://mirrors.aliyun.com
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    (sed -i "s|http://deb.debian.org|${DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources 2>/dev/null || true) && \
    (sed -i "s|http://deb.debian.org|${DEBIAN_MIRROR}|g" /etc/apt/sources.list 2>/dev/null || true) && \
    apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates ffmpeg
ADD https://astral.sh/uv/install.sh /uv-install.sh
RUN sh /uv-install.sh && rm /uv-install.sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app
# W5D3 — 国内构建 PyPI 直连 50KB/s 且大量超时,切清华镜像后稳定 10MB/s+。
# `UV_INDEX_URL` 是 uv 0.5+ / 老版本都认的环境变量。海外构建保持空字符串
# 走默认 PyPI 即可(`UV_INDEX_URL_OVERRIDE` 设了优先级最高,留给海外 CI)。
# Aliyun 跟腾讯云同区,wheel 也在 Aliyun 自己 CDN,不会回源 Fastly(清华
# mirror 只 mirror index、wheel 还是从 Fastly 拿,腾讯云出口到 Fastly 抽风
# 会让 uv sync 卡在 retry loop)。海外 CI 用 --build-arg 覆盖。
# W5D3 — uv 0.11+ 用 UV_DEFAULT_INDEX(主 index),UV_INDEX_URL 是 pip 兼容
# 的别名(同效)。两个都 set,确保任意版本 uv 都 honor。Tsinghua TUNA 自己
# host wheel 文件(不像 Aliyun 只 mirror index),从腾讯云直连快且稳。
ARG UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV UV_DEFAULT_INDEX=${UV_INDEX_URL} \
    UV_INDEX_URL=${UV_INDEX_URL}

# ---- Layer A: 3rd-party deps (HEAVY, rarely changes) ----
# `--no-install-project` 跳过本地 agent 包(下一层装),所以这一层只依赖
# pyproject.toml + uv.lock。改 src 不会让这层失效;只有 pyproject 改动才会。
# Cache mount: /root/.cache/uv 把 wheel 缓存留到下一次 build,加新 dep 只下增量。
# CLI flag `--default-index` 显式传 — 最强保险,即使 env var 因某种原因被
# 吃掉,CLI 也会 override lockfile 里硬编码的 https://pypi.org/simple URL。
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project \
        --default-index ${UV_INDEX_URL}

# ---- Layer B: 本地 agent 包(LIGHT, src 每改必跑) ----
# 只复制 src/,然后 uv sync 在 deps 都装好的前提下只装 file:///app 本地包。
# 实测 ~3-5s。
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev \
        --default-index ${UV_INDEX_URL}

# Persistent volume for SQLite + run logs
VOLUME ["/app/data"]

EXPOSE 8765 8766

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

CMD ["uv", "run", "python", "-m", "agent.server"]
