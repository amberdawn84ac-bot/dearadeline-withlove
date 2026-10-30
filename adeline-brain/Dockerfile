# Supply Node/npm explicitly: Prisma's CLI must not bootstrap nodeenv at startup.
FROM node:22-bookworm-slim AS node

# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libatomic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt requirements.lock ./
RUN python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir -r requirements.lock

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

RUN apt-get update && apt-get install -y --no-install-recommends \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system adeline \
    && adduser --system --ingroup adeline --no-create-home adeline

WORKDIR /app

# Copy entire venv from builder — executables (including prisma CLI) stay on PATH
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"
ENV PRISMA_USE_GLOBAL_NODE=true \
    PRISMA_BINARY_CACHE_DIR=/opt/prisma-cache

# Fetch CLI/engines while building, where failure is visible and reproducible.
# Keep the same cache path for the unprivileged runtime user and HOME=/tmp.
RUN node --version && npm --version && prisma version

COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY prisma/ ./prisma/
COPY entrypoint.sh .

RUN chmod +x entrypoint.sh \
    && chown -R adeline:adeline /app /opt/prisma-cache

USER adeline

# Verify the packaged CLI also works for the unprivileged runtime user.
RUN prisma version

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
