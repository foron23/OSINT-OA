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
#   3. Guarda la sesión en el volumen persistente
# =============================================================================

set -e

CONTAINER_NAME="osint-telegram-setup"
IMAGE_NAME="osint-aggregator:latest"

echo "=============================================="
echo "OSINT News Aggregator - Telegram MCP Setup"
echo "=============================================="
echo ""

# Check for required environment variables
if [ -z "$TG_APP_ID" ] || [ -z "$TG_API_HASH" ]; then
    echo "ERROR: TG_APP_ID and TG_API_HASH must be set"
    echo ""
    echo "1. Go to https://my.telegram.org"
    echo "2. Create an application"
    echo "3. Set environment variables:"
    echo "   export TG_APP_ID=your_app_id"
    echo "   export TG_API_HASH=your_api_hash"
    echo ""
    exit 1
fi

echo "Building Docker image..."
docker build -t "$IMAGE_NAME" .

echo ""
echo "Starting Telegram MCP authentication..."
echo "You will be prompted for your phone number and verification code."
echo ""

# Run telegram-mcp interactively for authentication
docker run -it --rm \
    --name "$CONTAINER_NAME" \
    -e TG_APP_ID="$TG_APP_ID" \
    -e TG_API_HASH="$TG_API_HASH" \
    -v osint-telegram-session:/app/data/telegram-session \
    "$IMAGE_NAME" \
    /app/bin/telegram-mcp

echo ""
echo "=============================================="
echo "Telegram authentication complete!"
echo "Session saved to volume: osint-telegram-session"
echo ""
echo "You can now run:"
echo "  docker-compose up -d"
echo "=============================================="
