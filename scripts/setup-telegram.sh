#!/bin/bash
# =============================================================================
# OSINT News Aggregator - Telegram MCP Setup Script
# =============================================================================
# Este script inicializa la sesión de Telegram MCP de forma interactiva.
# Debe ejecutarse UNA VEZ antes de desplegar en producción.
#
# Uso:
#   ./scripts/setup-telegram.sh
#
# El proceso:
#   1. Construye el contenedor
#   2. Ejecuta telegram-mcp interactivamente para autenticación
#   3. Guarda la sesión en el directorio ./telegram-session (bind mount)
# =============================================================================

set -e

CONTAINER_NAME="osint-telegram-setup"
IMAGE_NAME="osint-aggregator:latest"
# Directorio de sesión en el host (relativo al script)
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SESSION_DIR="${TELEGRAM_SESSION_HOST_PATH:-$SCRIPT_DIR/telegram-session}"

echo "=============================================="
echo "OSINT News Aggregator - Telegram MCP Setup"
echo "=============================================="
echo ""
echo "Session directory: $SESSION_DIR"
echo ""

# Crear directorio de sesión si no existe
mkdir -p "$SESSION_DIR"

# Check for required environment variables
if [ -z "$TG_APP_ID" ] || [ -z "$TG_API_HASH" ]; then
    # Intentar cargar desde .env
    if [ -f "$SCRIPT_DIR/.env" ]; then
        echo "Loading environment from .env..."
        export $(grep -E '^TG_APP_ID=|^TG_API_HASH=' "$SCRIPT_DIR/.env" | xargs)
    fi
    
    if [ -z "$TG_APP_ID" ] || [ -z "$TG_API_HASH" ]; then
        echo "ERROR: TG_APP_ID and TG_API_HASH must be set"
        echo ""
        echo "1. Go to https://my.telegram.org"
        echo "2. Create an application"
        echo "3. Set environment variables in .env or:"
        echo "   export TG_APP_ID=your_app_id"
        echo "   export TG_API_HASH=your_api_hash"
        echo ""
        exit 1
    fi
fi

echo "Building Docker image..."
docker build -t "$IMAGE_NAME" -f "$SCRIPT_DIR/Dockerfile" "$SCRIPT_DIR"

echo ""
echo "Starting Telegram MCP authentication..."
echo "You will be prompted for your phone number and verification code."
echo ""

# Run telegram-mcp interactively for authentication
# Usar bind mount al directorio del host en lugar de volumen Docker
docker run -it --rm \
    --name "$CONTAINER_NAME" \
    -e TG_APP_ID="$TG_APP_ID" \
    -e TG_API_HASH="$TG_API_HASH" \
    -v "$SESSION_DIR:/app/data/telegram-session" \
    "$IMAGE_NAME" \
    /app/bin/telegram-mcp

echo ""
echo "=============================================="
echo "Telegram authentication complete!"
echo "Session saved to: $SESSION_DIR"
echo ""
echo "You can now run:"
echo "  docker-compose up -d"
echo "=============================================="
