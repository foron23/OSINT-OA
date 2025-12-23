#!/bin/bash
# =============================================================================
# OSINT OA - Deploy Script
# =============================================================================
# Script para desplegar la aplicación en un servidor nuevo
#
# Uso:
#   ./deploy.sh              # Despliegue completo
#   ./deploy.sh --build      # Forzar rebuild de imagen
#   ./deploy.sh --pull       # Pull de imagen pre-construida (si existe)
#   ./deploy.sh --down       # Detener servicios
#   ./deploy.sh --logs       # Ver logs
#   ./deploy.sh --status     # Ver estado
# =============================================================================

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuración
COMPOSE_FILE="docker-compose.prod.yml"
PROJECT_NAME="osint-oa"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# =============================================================================
# Verificaciones Previas
# =============================================================================
check_requirements() {
    log_step "Checking requirements..."
    
    # Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Install it first:"
        echo "  curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    
    # Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose v2 is not installed."
        exit 1
    fi
    
    # Archivo .env
    if [ ! -f ".env" ]; then
        log_warn ".env file not found. Creating from template..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_warn "Please edit .env with your API keys before continuing"
            log_warn "  nano .env"
            exit 1
        else
            log_error ".env.example not found!"
            exit 1
        fi
    fi
    
    # Verificar OPENAI_API_KEY
    if grep -q "your-openai-api-key" .env; then
        log_error "Please configure OPENAI_API_KEY in .env file"
        exit 1
    fi
    
    log_info "All requirements satisfied"
}

# =============================================================================
# Build
# =============================================================================
build() {
    log_step "Building Docker image..."
    docker compose -f "$COMPOSE_FILE" build --no-cache
    log_info "Build complete"
}

# =============================================================================
# Deploy
# =============================================================================
deploy() {
    log_step "Deploying OSINT OA..."
    
    # Crear directorios si no existen
    mkdir -p data logs
    
    # Construir si es necesario
    if [ "$1" = "--build" ]; then
        build
    fi
    
    # Levantar servicios
    docker compose -f "$COMPOSE_FILE" up -d
    
    # Esperar a que esté listo
    log_step "Waiting for service to be healthy..."
    sleep 5
    
    # Verificar estado
    if docker compose -f "$COMPOSE_FILE" ps | grep -q "healthy"; then
        log_info "Deployment successful!"
        echo ""
        echo "  Application running at: http://localhost:${HOST_PORT:-5000}"
        echo "  View logs: ./deploy.sh --logs"
        echo "  Check status: ./deploy.sh --status"
        echo ""
    else
        log_warn "Service starting... Check logs if issues persist:"
        echo "  docker compose -f $COMPOSE_FILE logs -f"
    fi
}

# =============================================================================
# Otros comandos
# =============================================================================
stop() {
    log_step "Stopping services..."
    docker compose -f "$COMPOSE_FILE" down
    log_info "Services stopped"
}

status() {
    log_step "Service status:"
    docker compose -f "$COMPOSE_FILE" ps
    echo ""
    log_step "Resource usage:"
    docker stats --no-stream $(docker compose -f "$COMPOSE_FILE" ps -q) 2>/dev/null || true
}

logs() {
    docker compose -f "$COMPOSE_FILE" logs -f
}

backup() {
    log_step "Creating backup..."
    BACKUP_NAME="osint-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    docker run --rm \
        -v osint-oa-data-prod:/data \
        -v "$(pwd)":/backup \
        alpine tar czf "/backup/$BACKUP_NAME" /data
    log_info "Backup created: $BACKUP_NAME"
}

# =============================================================================
# Main
# =============================================================================
case "$1" in
    --build)
        check_requirements
        deploy --build
        ;;
    --down|--stop)
        stop
        ;;
    --logs)
        logs
        ;;
    --status)
        status
        ;;
    --backup)
        backup
        ;;
    --help)
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  (none)     Deploy application"
        echo "  --build    Force rebuild before deploy"
        echo "  --down     Stop all services"
        echo "  --logs     View application logs"
        echo "  --status   Show service status"
        echo "  --backup   Backup data volumes"
        echo "  --help     Show this help"
        ;;
    *)
        check_requirements
        deploy
        ;;
esac
