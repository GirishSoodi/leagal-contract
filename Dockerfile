# ============================================
# 🏗️ Builder Stage
# ============================================
ARG BASE_IMAGE=ghcr.io/meta-pytorch/openenv-base:latest
FROM ${BASE_IMAGE} AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    rm -rf /var/lib/apt/lists/*

# Copy full project
COPY . /app

# Install uv if not present
RUN if ! command -v uv >/dev/null 2>&1; then \
        curl -LsSf https://astral.sh/uv/install.sh | sh && \
        mv /root/.local/bin/uv /usr/local/bin/uv && \
        mv /root/.local/bin/uvx /usr/local/bin/uvx; \
    fi

# Install dependencies (cached)
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -f uv.lock ]; then \
        uv sync --frozen --no-install-project --no-editable; \
    else \
        uv sync --no-install-project --no-editable; \
    fi

RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -f uv.lock ]; then \
        uv sync --frozen --no-editable; \
    else \
        uv sync --no-editable; \
    fi


# ============================================
# 🚀 Runtime Stage
# ============================================
FROM ${BASE_IMAGE}

WORKDIR /app

# Copy virtual environment
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY --from=builder /app /app

# Activate venv
ENV PATH="/app/.venv/bin:$PATH"

# 🔥 CRITICAL: Ensure package imports work
ENV PYTHONPATH="/app:$PYTHONPATH"

# Environment variables
ENV DATA_PATH="/app/server/processed/contracts.json"
ENV ENABLE_WEB_INTERFACE=true

# Health check (used by validator)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 🔥 FIXED ENTRYPOINT (IMPORTANT)
CMD ["uvicorn", "legalcontractreview.server.app:app", "--host", "0.0.0.0", "--port", "8000"]