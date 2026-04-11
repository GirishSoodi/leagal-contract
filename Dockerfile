ARG BASE_IMAGE=ghcr.io/meta-pytorch/openenv-base:latest
FROM ${BASE_IMAGE}

WORKDIR /app

# Install system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx

# Install dependencies
RUN uv sync --no-install-project --no-editable || true
RUN uv sync --no-editable || true

# Install project
RUN pip install --no-cache-dir .

# Debug check (optional but useful)
RUN python -c "import legalcontractreview; print(len(legalcontractreview.TASKS))"

ENV PYTHONPATH="/app:$PYTHONPATH"

# Health check
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1

# ✅ FIXED ENTRYPOINT
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]