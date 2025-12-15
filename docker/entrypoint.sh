#!/bin/bash
# =============================================================================
# OSINT News Aggregator - Docker Entrypoint Script
# =============================================================================
# Este script se ejecuta al iniciar el contenedor y realiza:
# 1. Validación de variables de entorno requeridas
# 2. Inicialización de la base de datos (si no existe)
# 3. Verificación de conectividad con servicios externos
# 4. Inicio de la aplicación
# =============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# Validación de Variables de Entorno
# =============================================================================
validate_env() {
    log_info "Validating environment variables..."
    
    local missing_required=()
    local missing_optional=()
    
    # Variables REQUERIDAS
    if [ -z "$OPENAI_API_KEY" ]; then
        missing_required+=("OPENAI_API_KEY")
    fi
    
    # Variables OPCIONALES (con warnings)
    if [ -z "$TELEGRAM_APP_ID" ] && [ -z "$TG_APP_ID" ]; then
        missing_optional+=("TELEGRAM_APP_ID/TG_APP_ID (Telegram integration disabled)")
    fi
    
    if [ -z "$TELEGRAM_API_HASH" ] && [ -z "$TG_API_HASH" ]; then
        missing_optional+=("TELEGRAM_API_HASH/TG_API_HASH (Telegram integration disabled)")
    fi
    
    if [ -z "$TAVILY_API_KEY" ]; then
        missing_optional+=("TAVILY_API_KEY (Using DuckDuckGo as fallback)")
    fi
    
    # Reportar variables faltantes
    if [ ${#missing_required[@]} -ne 0 ]; then
        log_error "Missing required environment variables:"
        for var in "${missing_required[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi
    
    if [ ${#missing_optional[@]} -ne 0 ]; then
        log_warn "Missing optional environment variables:"
        for var in "${missing_optional[@]}"; do
            echo "  - $var"
        done
    fi
    
    log_info "Environment validation complete"
}

# =============================================================================
# Inicialización de Base de Datos
# =============================================================================
init_database() {
    log_info "Checking database..."
    
    DB_DIR=$(dirname "$DATABASE_PATH")
    
    # Crear directorio si no existe
    if [ ! -d "$DB_DIR" ]; then
        log_info "Creating database directory: $DB_DIR"
        mkdir -p "$DB_DIR"
    fi
    
    # Arreglar permisos del directorio de datos (necesario cuando se monta volumen)
    # El volumen puede haber sido creado por root, necesitamos hacerlo escribible
    if [ ! -w "$DB_DIR" ]; then
        log_warn "Database directory not writable, attempting to fix permissions..."
        # Si somos root (en entrypoint antes de cambiar usuario), arreglamos permisos
        if [ "$(id -u)" = "0" ]; then
            chown -R osint:osint "$DB_DIR" 2>/dev/null || true
            chmod -R 755 "$DB_DIR" 2>/dev/null || true
        fi
    fi
    
    # Verificar permisos de nuevo
    if [ ! -w "$DB_DIR" ]; then
        log_error "Cannot write to database directory: $DB_DIR"
        log_error "Please ensure the volume has correct permissions:"
        log_error "  docker exec -u root <container> chown -R osint:osint /app/data"
        exit 1
    fi
    
    # Inicializar base de datos con Python
    if [ ! -f "$DATABASE_PATH" ]; then
        log_info "Initializing new database..."
        python -c "
from db import init_db
init_db()
print('Database initialized successfully')
"
    else
        log_info "Database exists at: $DATABASE_PATH"
        # Verificar que la base de datos es escribible
        if [ ! -w "$DATABASE_PATH" ]; then
            log_warn "Database file not writable, attempting to fix..."
            chmod 644 "$DATABASE_PATH" 2>/dev/null || true
        fi
    fi
}

# =============================================================================
# Verificación de Telegram MCP
# =============================================================================
check_telegram_mcp() {
    log_info "Checking Telegram MCP binary..."
    
    if [ -f "$TELEGRAM_MCP_PATH" ]; then
        if [ -x "$TELEGRAM_MCP_PATH" ]; then
            log_info "Telegram MCP binary found and executable"
        else
            log_warn "Telegram MCP binary found but not executable, fixing..."
            chmod +x "$TELEGRAM_MCP_PATH"
        fi
    else
        log_warn "Telegram MCP binary not found at: $TELEGRAM_MCP_PATH"
        log_warn "Telegram integration will not be available"
    fi
    
    # Verificar sesión de Telegram
    if [ -d "$TELEGRAM_SESSION_PATH" ]; then
        log_info "Telegram session directory exists"
    else
        log_info "Creating Telegram session directory..."
        mkdir -p "$TELEGRAM_SESSION_PATH"
    fi
}

# =============================================================================
# Mostrar Configuración
# =============================================================================
show_config() {
    log_info "=== OSINT Aggregator Configuration ==="
    echo "  Flask Debug: ${FLASK_DEBUG:-0}"
    echo "  Database: ${DATABASE_PATH}"
    echo "  Telegram MCP: ${TELEGRAM_MCP_PATH}"
    echo "  Telegram MCP Service: ${TELEGRAM_MCP_USE_SERVICE:-false}"
    echo "  Telegram MCP Service URL: ${TELEGRAM_MCP_SERVICE_URL:-N/A}"
    echo "  OpenAI Model: ${OPENAI_MODEL:-gpt-4o-mini}"
    echo "  Gunicorn Workers: ${GUNICORN_WORKERS:-4}"
    echo "  Gunicorn Threads: ${GUNICORN_THREADS:-2}"
    echo "============================================="
}

# =============================================================================
# Preparar logs directory
# =============================================================================
prepare_logs() {
    if [ ! -d "/app/logs" ]; then
        mkdir -p /app/logs
    fi
    # Asegurar permisos
    touch /app/logs/supervisord.log 2>/dev/null || true
}

# =============================================================================
# Arreglar permisos de volúmenes (ejecutar como root)
# =============================================================================
fix_permissions() {
    # Solo ejecutar si somos root
    if [ "$(id -u)" != "0" ]; then
        return 0
    fi
    
    log_info "Fixing volume permissions..."
    
    # Arreglar permisos del directorio de datos
    if [ -d "/app/data" ]; then
        chown -R osint:osint /app/data 2>/dev/null || true
        chmod -R 755 /app/data 2>/dev/null || true
    fi
    
    # Arreglar permisos del directorio de logs
    if [ -d "/app/logs" ]; then
        chown -R osint:osint /app/logs 2>/dev/null || true
        chmod -R 755 /app/logs 2>/dev/null || true
    fi
    
    # Arreglar permisos de la sesión de Telegram
    if [ -d "/app/data/telegram-session" ]; then
        chown -R osint:osint /app/data/telegram-session 2>/dev/null || true
        chmod -R 755 /app/data/telegram-session 2>/dev/null || true
    fi
    
    log_info "Permissions fixed"
}

# =============================================================================
# Main
# =============================================================================
main() {
    log_info "Starting OSINT Aggregator..."
    
    # Arreglar permisos de volúmenes (si somos root)
    fix_permissions
    
    # Ejecutar validaciones
    validate_env
    init_database
    check_telegram_mcp
    prepare_logs
    show_config
    
    # Detectar modo de ejecución
    if [ "$1" = "supervisord" ]; then
        log_info "Starting in MULTI-SERVICE mode (Flask + Telegram MCP Service)"
        log_info "  - Flask API: http://0.0.0.0:5000"
        log_info "  - Telegram MCP Service: http://0.0.0.0:5001"
    elif [ "$1" = "gunicorn" ]; then
        log_info "Starting in SINGLE-SERVICE mode (Flask only)"
        log_info "  - Flask API: http://0.0.0.0:5000"
        log_info "  - Telegram MCP: on-demand (direct binary calls)"
    fi
    
    log_info "Starting application..."
    
    # Ejecutar el comando pasado
    exec "$@"
}

# Ejecutar main con todos los argumentos
main "$@"
