# 🐳 Guía de Despliegue con Docker

Este documento describe cómo desplegar OSINT News Aggregator en cualquier servidor usando Docker.

## 📋 Índice

1. [Requisitos Previos](#requisitos-previos)
2. [Arquitectura](#arquitectura)
3. [Despliegue Rápido](#despliegue-rápido)
4. [Configuración Detallada](#configuración-detallada)
5. [Telegram MCP Setup](#telegram-mcp-setup)
6. [Operaciones](#operaciones)
7. [Troubleshooting](#troubleshooting)

---

## 📦 Requisitos Previos

### En el servidor de destino:

```bash
# Docker Engine (20.10+)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Verificar instalación
docker --version
docker compose version
```

### Credenciales necesarias:

| Variable | Requerida | Descripción | Obtener en |
|----------|-----------|-------------|------------|
| `OPENAI_API_KEY` | ✅ Sí | API key de OpenAI | [platform.openai.com](https://platform.openai.com/api-keys) |
| `TELEGRAM_APP_ID` | ⭕ Opcional | API ID de Telegram | [my.telegram.org](https://my.telegram.org/apps) |
| `TELEGRAM_API_HASH` | ⭕ Opcional | API Hash de Telegram | [my.telegram.org](https://my.telegram.org/apps) |
| `TAVILY_API_KEY` | ⭕ Opcional | Tavily Search API | [tavily.com](https://tavily.com/) |

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    OSINT News Aggregator                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Docker Container (Supervisord)              │   │
│  │                                                          │   │
│  │  ┌──────────────────┐    ┌──────────────────────────┐  │   │
│  │  │   Gunicorn       │    │   Telegram MCP Service   │  │   │
│  │  │   (Flask API)    │    │   (HTTP wrapper)         │  │   │
│  │  │   Puerto 5000    │    │   Puerto 5001            │  │   │
│  │  │                  │    │                          │  │   │
│  │  │  LangChain       │◄──►│  ┌──────────────────┐   │  │   │
│  │  │  Agents          │HTTP│  │  telegram-mcp    │   │  │   │
│  │  │                  │    │  │  (Go binary)     │   │  │   │
│  │  └────────┬─────────┘    │  └──────────────────┘   │  │   │
│  │           │              └──────────────────────────┘  │   │
│  │           ▼                                             │   │
│  │  ┌──────────────────┐                                   │   │
│  │  │   /app/data      │ ◄── Volume: osint-data           │   │
│  │  │   - osint.db     │                                   │   │
│  │  │   - reports/     │                                   │   │
│  │  │   - telegram-    │ ◄── Volume: telegram-session     │   │
│  │  │     session/     │                                   │   │
│  │  └──────────────────┘                                   │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                      Port 5000                                  │
│                           ▼                                     │
└─────────────────────────────────────────────────────────────────┘
                            │
                    ┌───────┴───────┐
                    │   Internet    │
                    │  - OpenAI API │
                    │  - Telegram   │
                    │  - Tavily     │
                    └───────────────┘
```

### Modos de Operación

El contenedor soporta **dos modos** de operación para Telegram MCP:

| Modo | Descripción | Uso |
|------|-------------|-----|
| **Multi-servicio** (default) | Supervisord ejecuta Flask + Telegram MCP Service en paralelo | Producción (más rápido) |
| **Single-servicio** | Solo Flask, Telegram MCP se ejecuta on-demand | Desarrollo o recursos limitados |

### Decisiones de Arquitectura

| Decisión | Justificación |
|----------|---------------|
| **Multi-stage build** | Reduce imagen de ~1.5GB a ~400MB eliminando build tools |
| **python:3.12-slim** | Balance entre tamaño y compatibilidad (Alpine causa problemas con lxml) |
| **Gunicorn gthread** | Óptimo para I/O intensivo (APIs externas) con 4 workers × 2 threads |
| **Supervisord** | Gestiona múltiples procesos (Flask + Telegram MCP) en un contenedor |
| **Tini init** | Manejo correcto de señales (SIGTERM) y prevención de zombies |
| **Non-root user** | Seguridad - el contenedor nunca corre como root |
| **Volúmenes nombrados** | Persistencia de datos entre actualizaciones |
| **Telegram MCP Service** | Conexión persistente = menor latencia vs ejecutar binario cada vez |

---

## 🚀 Despliegue Rápido

### Opción A: Script automático

```bash
# 1. Clonar/copiar el proyecto
cd /opt/osint-aggregator

# 2. Configurar variables de entorno
cp .env.example .env
nano .env  # Editar con tus API keys

# 3. Ejecutar deploy
chmod +x deploy.sh
./deploy.sh
```

### Opción B: Manual con docker-compose

```bash
# 1. Configurar .env
cp .env.example .env
# Editar .env con tus credenciales

# 2. Construir imagen
docker compose -f docker-compose.prod.yml build

# 3. Levantar servicios
docker compose -f docker-compose.prod.yml up -d

# 4. Verificar estado
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

### Acceder a la aplicación

```
http://tu-servidor:5000
```

---

## ⚙️ Configuración Detallada

### Variables de Entorno (.env)

#### Requeridas

```env
# OpenAI (REQUERIDO)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini  # Recomendado para balance costo/rendimiento
```

#### Telegram (Opcional pero recomendado)

```env
# Credenciales de API de Telegram
TELEGRAM_APP_ID=12345678
TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef

# Dialog de destino para reportes
TELEGRAM_TARGET_DIALOG=MiCanal
```

#### Búsqueda (Opcional)

```env
# Tavily es preferido (optimizado para LLMs)
TAVILY_API_KEY=tvly-...

# Si no tienes Tavily, se usa DuckDuckGo automáticamente
```

#### Producción

```env
FLASK_DEBUG=0
SECRET_KEY=tu-clave-secreta-generada

# Gunicorn (ajustar según CPU del servidor)
GUNICORN_WORKERS=4    # Recomendado: 2-4 × núcleos CPU
GUNICORN_THREADS=2
GUNICORN_TIMEOUT=120  # Alto para operaciones OSINT lentas
```

### Recursos del Servidor

| Escenario | CPU | RAM | Notas |
|-----------|-----|-----|-------|
| Mínimo | 1 core | 1 GB | Funcional pero lento |
| Recomendado | 2 cores | 2 GB | Buen rendimiento |
| Producción | 4 cores | 4 GB | Alto throughput |

---

## 📱 Telegram MCP Setup

El binario `telegram-mcp` requiere autenticación inicial con tu cuenta de Telegram.

### Primera vez (después del despliegue)

```bash
# Entrar al contenedor
docker compose -f docker-compose.prod.yml exec osint-aggregator bash

# Ejecutar script de setup
python scripts/setup_telegram.py
```

El script te guiará para:
1. Verificar credenciales
2. Iniciar autenticación
3. Ingresar código de verificación (enviado a tu Telegram)
4. Guardar sesión

### Importante

- La sesión se guarda en el volumen `telegram-session`
- **NO** se pierde al actualizar el contenedor
- Solo hay que re-autenticar si eliminas el volumen

---

## 🔧 Operaciones

### Logs

```bash
# Todos los logs
docker compose -f docker-compose.prod.yml logs -f

# Solo últimas 100 líneas
docker compose -f docker-compose.prod.yml logs --tail=100

# Con script
./deploy.sh --logs
```

### Status

```bash
docker compose -f docker-compose.prod.yml ps

# Uso de recursos
docker stats osint-news-aggregator-prod
```

### Actualizar

```bash
# Pull de código nuevo
git pull

# Rebuild y restart
docker compose -f docker-compose.prod.yml up -d --build
```

### Backup

```bash
# Backup completo de datos
./deploy.sh --backup

# Manual
docker run --rm \
  -v osint-news-data-prod:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/backup-$(date +%Y%m%d).tar.gz /data
```

### Restore

```bash
# Detener servicio
docker compose -f docker-compose.prod.yml down

# Restaurar backup
docker run --rm \
  -v osint-news-data-prod:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/backup-YYYYMMDD.tar.gz -C /

# Reiniciar
docker compose -f docker-compose.prod.yml up -d
```

### Parar/Eliminar

```bash
# Solo parar (preserva datos)
docker compose -f docker-compose.prod.yml down

# Parar y eliminar volúmenes (¡DESTRUCTIVO!)
docker compose -f docker-compose.prod.yml down -v
```

---

## 🐛 Troubleshooting

### Container no arranca

```bash
# Ver logs de arranque
docker compose -f docker-compose.prod.yml logs --tail=50

# Verificar .env
grep OPENAI_API_KEY .env  # Debe mostrar la key (no el placeholder)
```

### Health check falla

```bash
# Verificar que la API responde
curl http://localhost:5000/api/runs

# Entrar al contenedor y verificar
docker compose -f docker-compose.prod.yml exec osint-aggregator curl localhost:5000/api/runs
```

### Error de permisos

```bash
# Verificar que los volúmenes tienen permisos correctos
docker compose -f docker-compose.prod.yml exec osint-aggregator ls -la /app/data
```

### Telegram no funciona

1. Verificar credenciales en `.env`:
   ```bash
   grep -E "TELEGRAM_APP_ID|TG_APP_ID" .env
   ```

2. Re-ejecutar setup:
   ```bash
   docker compose -f docker-compose.prod.yml exec osint-aggregator python scripts/setup_telegram.py
   ```

### Out of memory

```bash
# Aumentar límites en docker-compose.prod.yml
deploy:
  resources:
    limits:
      memory: 8G  # Aumentar según necesidad
```

---

## 📊 Monitoreo (Opcional)

### Con Prometheus + Grafana

Añadir a `docker-compose.prod.yml`:

```yaml
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

### Health Endpoint

La API expone `/api/runs` que puede usarse para monitoreo externo.

---

## 🔒 Seguridad en Producción

1. **Reverse Proxy**: Usar nginx/traefik con HTTPS
2. **Firewall**: Solo exponer puerto 443 (HTTPS)
3. **Secrets**: Usar Docker secrets o vault para API keys
4. **Updates**: Mantener imagen base actualizada

Ejemplo con nginx:

```nginx
server {
    listen 443 ssl;
    server_name osint.tudominio.com;
    
    ssl_certificate /etc/letsencrypt/live/osint.tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/osint.tudominio.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📝 Licencia

Este proyecto está bajo licencia MIT.
