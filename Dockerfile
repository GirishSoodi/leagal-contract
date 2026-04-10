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

# Copy project files
COPY . /app

# Install uv if not present
RUN if ! command -v uv >/dev/null 2>&1; then \
        curl -LsSf https://astral.sh/uv/install.sh | sh && \
        mv /root/.local/bin/uv /usr/local/bin/uv && \
        mv /root/.local/bin/uvx /usr/local/bin/uvx; \
    fi

# Install dependencies (WITHOUT installing project)
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -f uv.lock ]; then \
        uv sync --frozen --no-install-project --no-editable; \
    else \
        uv sync --no-install-project --no-editable; \
    fi

# Install dependencies (full sync)
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -f uv.lock ]; then \
        uv sync --frozen --no-editable; \
    else \
        uv sync --no-editable; \
    fi

# 🔥 CRITICAL FIX: install your package properly
RUN pip install --no-cache-dir .


RUN python -c "import legalcontractreview; print(len(legalcontractreview.TASKS))"


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

# Ensure Python can find your package
ENV PYTHONPATH="/app:$PYTHONPATH"

# Environment variables
ENV DATA_PATH="/app/server/processed/contracts.json"
ENV ENABLE_WEB_INTERFACE=true

# Health check (required by validator)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ✅ Correct entrypoint (now works because package is installed)
CMD ["uvicorn", "legalcontractreview.server.app:app", "--host", "0.0.0.0", "--port", "8000"]