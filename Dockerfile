# =============================================================================
# OSINT OA - Dockerfile
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
LABEL maintainer="OSINT OA"
LABEL description="OSINT OA with LangChain ReAct Agents"
LABEL version="1.0.0"

# Install runtime dependencies only
# - git: Required by bbot for some modules
# - dns-utils: DNS lookups for OSINT tools  
# - whois: Domain WHOIS lookups
# - wget, unzip: For downloading binaries
# - supervisor: Process manager for Flask + Telegram Listener
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    curl \
    wget \
    unzip \
    git \
    dnsutils \
    whois \
    supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && mkdir -p /etc/supervisor/conf.d

# Install Go tools (Amass and PhoneInfoga) as pre-compiled binaries
# Amass - OWASP attack surface mapping
RUN curl -L -o /tmp/amass.zip https://github.com/owasp-amass/amass/releases/download/v4.2.0/amass_Linux_amd64.zip && \
    unzip -j /tmp/amass.zip "amass_Linux_amd64/amass" -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/amass && \
    rm /tmp/amass.zip

# PhoneInfoga - Phone number OSINT
RUN curl -sSL https://github.com/sundowndev/phoneinfoga/releases/download/v2.11.0/phoneinfoga_Linux_x86_64.tar.gz | \
    tar -xz -C /usr/local/bin phoneinfoga && \
    chmod +x /usr/local/bin/phoneinfoga

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

# Create data directories for SQLite and Telegram session
RUN mkdir -p /app/data /app/data/telegram-session /app/logs && chown -R osint:osint /app/data /app/logs

# Copy supervisord configuration
COPY --chown=osint:osint docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_APP=app.py
ENV DATABASE_PATH=/app/data/osint.db
ENV TELEGRAM_SESSION_PATH=/app/data/telegram-session

# Expose Flask port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/runs || exit 1

# Switch to root for supervisord (it will drop to osint for processes)
USER root

# Default command - use supervisord to manage Flask + Telegram Listener
# For Flask only, use: docker run ... python app.py
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
