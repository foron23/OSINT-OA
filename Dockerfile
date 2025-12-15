# =============================================================================
# OSINT News Aggregator - Dockerfile
# =============================================================================
# Multi-stage build for optimized production image
#
# Decisiones de arquitectura:
# 1. python:3.12-slim como base - balance entre tamaño y compatibilidad
# 2. Multi-stage para reducir imagen final (no incluye build tools)
# 3. Non-root user para seguridad
# 4. Telegram MCP binario Go incluido (pre-compilado x86-64)
# 5. Healthcheck integrado para orquestadores
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies with uv (10-100x faster than pip)
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install build dependencies + curl for uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv - The fastest Python package manager
ENV UV_VERSION=0.5.24
RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV="/opt/venv"

# Install Python dependencies with uv
COPY requirements.txt .
RUN uv pip install --no-cache -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Labels
LABEL maintainer="OSINT News Aggregator"
LABEL description="OSINT News Aggregator with LangChain ReAct Agents"
LABEL version="1.0.0"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r osint && useradd -r -g osint osint

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=osint:osint app.py .
COPY --chown=osint:osint pytest.ini .
COPY --chown=osint:osint config/ ./config/
COPY --chown=osint:osint agents/ ./agents/
COPY --chown=osint:osint tools/ ./tools/
COPY --chown=osint:osint integrations/ ./integrations/
COPY --chown=osint:osint api/ ./api/
COPY --chown=osint:osint db/ ./db/
COPY --chown=osint:osint frontend/ ./frontend/
COPY --chown=osint:osint osint_mcp/ ./osint_mcp/
COPY --chown=osint:osint scripts/ ./scripts/
COPY --chown=osint:osint tests/ ./tests/

# Copy Telegram MCP binary (Go binary, pre-compiled for x86-64 Linux)
COPY --chown=osint:osint bin/telegram-mcp /app/bin/telegram-mcp
RUN chmod +x /app/bin/telegram-mcp

# Create data directory for SQLite and Telegram session
RUN mkdir -p /app/data && chown -R osint:osint /app/data

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_APP=app.py
ENV DATABASE_PATH=/app/data/osint.db
ENV TELEGRAM_MCP_PATH=/app/bin/telegram-mcp

# Expose Flask port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/runs || exit 1

# Switch to non-root user
USER osint

# Default command - run Flask with gunicorn for production
CMD ["python", "app.py"]
