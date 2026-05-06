# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libatomic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir -r requirements.txt

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system adeline \
    && adduser --system --ingroup adeline --no-create-home adeline

WORKDIR /app

# Copy entire venv from builder — executables (including prisma CLI) stay on PATH
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY prisma/ ./prisma/
COPY entrypoint.sh .

RUN chmod +x entrypoint.sh \
    && chown -R adeline:adeline /app

USER adeline

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
