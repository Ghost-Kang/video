# OpenRHTV Cascade — backend (W5D2 deploy)
#
# Image: python:3.12-slim + uv + ffmpeg (yt-dlp dep)
# Entry: python -m agent.server  (WS :8765 + HTTP :8766)
# Volume: /data → SQLite + ARK cache
# Env:    see .env.example — at minimum ARK_API_KEY, INVITE_CODES,
#         CASCADE_UPSTREAM=doubao_direct, TOPRADOR_RESOLVER_MODE=douyin_share

FROM python:3.12-slim AS builder

# uv = fastest Python package manager. We pin to a known good version.
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates ffmpeg \
    && rm -rf /var/lib/apt/lists/*
ADD https://astral.sh/uv/install.sh /uv-install.sh
RUN sh /uv-install.sh && rm /uv-install.sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app
# COPY src BEFORE uv sync — uv sync builds the local "agent" package
# (file:///app) and needs src/agent/__init__.py to exist before resolving.
# Trades layer cache (any src edit invalidates uv sync) for correctness.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

# Persistent volume for SQLite + run logs
VOLUME ["/app/data"]

EXPOSE 8765 8766

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

CMD ["uv", "run", "python", "-m", "agent.server"]
