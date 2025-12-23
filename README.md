# 🔍 OSINT Agentic Operations

> ⚠️ **DISCLAIMER: USO ÉTICO Y RESPONSABLE**
> 
> Esta herramienta está diseñada **exclusivamente para fines educativos, de investigación y uso ético**. Al utilizar este software, usted acepta:
>
> - 🔒 **Respetar la privacidad**: No recopilar información personal sin consentimiento legal
> - ⚖️ **Cumplir la ley**: Obedecer todas las leyes locales, nacionales e internacionales aplicables
> - 🎯 **Uso legítimo**: Utilizar solo para auditorías autorizadas, investigaciones de seguridad propias, o investigación académica
> - 🚫 **Prohibido**: Acoso, stalking, doxing, fraude, o cualquier actividad maliciosa
> - 📝 **Responsabilidad**: Los desarrolladores no se hacen responsables del uso indebido de esta herramienta
>
> **El uso indebido de técnicas OSINT puede tener consecuencias legales graves.**

---

**Sistema de Operaciones OSINT Agéntico** - Una plataforma avanzada de inteligencia de código abierto basada en agentes LangChain/LangGraph que colaboran para realizar investigaciones exhaustivas.

[![Tests](https://img.shields.io/badge/tests-222%20passed-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-ReAct-orange)](https://langchain.com)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 🎯 Descripción

OSINT Agentic Operations es un sistema donde **múltiples agentes especializados colaboran** para realizar investigaciones de inteligencia de código abierto. A diferencia de herramientas tradicionales, este sistema:

- **Colaboración Multi-Agente**: Los agentes trabajan juntos, compartiendo hallazgos y evidencias
- **Extracción Automática de IOCs**: Cada agente extrae y reporta Indicadores de Compromiso
- **Trazabilidad Completa**: Cada acción, decisión y hallazgo queda registrado
- **Integración Telegram**: Recibe comandos y publica reportes automáticamente

## ✨ Características

### 🤖 Sistema de Agentes
- **ControlAgent**: Orquestador que planifica y coordina investigaciones multi-agente
- **ConsolidatorAgent**: Publicación de reportes a canales Telegram
- **10 agentes especializados OSINT**: Búsqueda, scraping, análisis de amenazas, IOCs, identidades, dominios
- **Patrón ReAct**: Reasoning + Acting con LangGraph
- **Evidencia estructurada**: Todos los agentes extraen IOCs, entidades y técnicas MITRE ATT&CK

### 🔬 Agentes Disponibles

#### 🎯 Agentes de Orquestación

| Agente | Función | Herramientas |
|--------|---------|--------------|
| **ControlAgent** | Orquesta investigaciones multi-agente, planifica estrategias y delega tareas | delegate_to_agent, list_agents, get_agent_info |
| **ConsolidatorAgent** | Publica reportes formateados a canales Telegram | telegram_publish_report |

#### 🔍 Agentes de Búsqueda

| Agente | Función | Herramientas |
|--------|---------|--------------|
| **TavilySearchAgent** | Búsqueda web AI-optimizada para OSINT | Tavily API |
| **DuckDuckGoSearchAgent** | Búsqueda privada sin tracking | DuckDuckGo |
| **GoogleDorkingAgent** | Búsqueda avanzada con operadores Google | Dork Builder |

#### 📊 Agentes de Análisis

| Agente | Función | Herramientas |
|--------|---------|--------------|
| **WebScraperAgent** | Extracción profunda de contenido web | Web Scraper, BeautifulSoup |
| **ThreatIntelAgent** | Análisis de inteligencia de amenazas | IOC Extractor, Tag Extractor |
| **IOCAnalysisAgent** | Extracción y análisis de Indicadores de Compromiso | IOC Extractor |
| **HybridOsintAgent** | Investigación completa multi-herramienta | Todas las herramientas |
| **ReportGeneratorAgent** | Generación de reportes estructurados | Tag Extractor, Templates |

#### 🕵️ Agentes de Identidad y Dominios

| Agente | Función | Herramientas |
|--------|---------|--------------|
| **MaigretAgent** | OSINT de usernames en 500+ plataformas | maigret_username_search, maigret_report |
| **BbotAgent** | Reconocimiento de dominios y superficie de ataque | bbot_subdomain_enum, bbot_web_recon, bbot_email_harvest |

### 🛠️ Herramientas OSINT Integradas

| Herramienta | Tipo | Descripción | API Key |
|-------------|------|-------------|---------|
| **Maigret** | Username | Búsqueda en 500+ plataformas | ❌ No |
| **BBOT** | Dominios | Subdominios, web recon, emails | ❌ No |
| **Holehe** | Email | Verificación en 100+ sitios | ❌ No |
| **Amass** | Dominios | OWASP subdomain enumeration | ❌ No |
| **PhoneInfoga** | Teléfono | OSINT de números telefónicos | ❌ No |
| **DuckDuckGo** | Búsqueda | Búsqueda web privada | ❌ No |
| **Tavily** | Búsqueda | Búsqueda AI-optimizada | ✅ Sí |

### 📊 Sistema de Evidencias
- **IOCs Soportados**: IP, Domain, URL, Hash (MD5/SHA1/SHA256), Email, CVE, Crypto
- **Entidades**: Threat Actors, Malware, Organizations, Personas
- **Técnicas**: Mapeo a MITRE ATT&CK
- **Confidence Scores**: Puntuación de confianza 0.0-1.0

### 📱 Integración Telegram
- Listener para comandos `/osint <query>`
- Publicación automática de reportes
- Diálogo interactivo con el sistema

## 📁 Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OSINT Agentic Operations                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        ORCHESTRATION LAYER                            │   │
│  │  ┌─────────────────┐    ┌──────────────────┐    ┌────────────────┐   │   │
│  │  │  ControlAgent   │───▶│  AgentRegistry   │───▶│ ConsolidatorAg │   │   │
│  │  │   (Planner)     │    │  (Discovery)     │    │   (Telegram)   │   │   │
│  │  └─────────────────┘    └──────────────────┘    └────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         SPECIALIZED AGENTS                            │   │
│  │                                                                       │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │   │   Tavily     │  │  DuckDuckGo  │  │   Google     │               │   │
│  │   │ SearchAgent  │  │ SearchAgent  │  │ DorkingAgent │               │   │
│  │   └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  │                                                                       │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │   │   Web        │  │   Threat     │  │    IOC       │               │   │
│  │   │ ScraperAgent │  │  IntelAgent  │  │ AnalysisAgen │               │   │
│  │   └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  │                                                                       │   │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │   │   Hybrid     │  │   Maigret    │  │    Bbot      │               │   │
│  │   │  OsintAgent  │  │    Agent     │  │    Agent     │               │   │
│  │   └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                           TOOLS LAYER                                 │   │
│  │   ┌─────────────────────────────────────────────────────────────┐    │   │
│  │   │  search.py  │  scraping.py  │  analysis.py  │  telegram.py  │    │   │
│  │   └─────────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         TRACING & EVIDENCE                            │   │
│  │   ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐    │   │
│  │   │   Traces    │  │  Evidence    │  │     IOC Repository       │    │   │
│  │   │  (Actions)  │  │  (Findings)  │  │  (Indicators Database)   │    │   │
│  │   └─────────────┘  └──────────────┘  └──────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                          DATA LAYER                                   │   │
│  │   ┌─────────────────────────────────────────────────────────────┐    │   │
│  │   │  SQLite: runs │ traces │ items │ indicators │ reports       │    │   │
│  │   └─────────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

                          EXTERNAL INTEGRATIONS

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram      │    │    OpenAI       │    │    Tavily       │
│   MCP Server    │◀──▶│    GPT-4o       │    │    Search API   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Instalación

### 1. Clonar y crear entorno virtual

```bash
git clone <repository>
cd ProyectoFinal
python -m venv venv
source venv/bin/activate  # Linux/Mac
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus API keys
```

Variables requeridas:
```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
TELEGRAM_TARGET_DIALOG=nombre_del_chat  # Para publicar reportes
```

### 4. Iniciar servicios

```bash
# Opción A: Desarrollo
python app.py

# Opción B: Docker Production
docker compose -f docker-compose.prod.yml up -d
```

## 📖 Uso

### API REST

```bash
# Ejecutar investigación
curl -X POST http://localhost:5000/api/collect \
  -H "Content-Type: application/json" \
  -d '{"query": "Latest ransomware attacks 2024", "depth": "standard"}'

# Ver investigaciones
curl http://localhost:5000/api/runs

# Ver trazas de una investigación
curl http://localhost:5000/api/runs/1/traces

# Resumen de evidencias
curl http://localhost:5000/api/runs/1/traces/summary
```

### Telegram

```
/osint investigate ransomware lockbit
/osint deep CVE-2024-21762
/osint quick bitcoin scam addresses
```

### Frontend

Accede a `http://localhost:5000` para el panel web con tema hacker (negro/rojo).

## 📱 Integración Telegram - Guía Completa

OSINT OA incluye un bot de Telegram completo que permite ejecutar investigaciones y consultar resultados directamente desde un chat.

### Comandos Disponibles

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `/osint <query>` | Iniciar investigación OSINT | `/osint ransomware attacks 2025` |
| `/search <query>` | Búsqueda rápida | `/search CVE-2024-21762` |
| `/runs` | Listar investigaciones recientes | `/runs` |
| `/run <id>` | Ver detalles de una investigación | `/run 42` |
| `/traces <id>` | Ver trazas de ejecución | `/traces 42` |
| `/status` | Ver estado del bot | `/status` |
| `/help` | Mostrar ayuda | `/help` |

### Lenguaje Natural

El bot también entiende solicitudes en lenguaje natural:

```
Investiga sobre APT29
Busca información sobre vulnerabilidades en Cisco
Analiza las últimas amenazas de ransomware
Investigate recent DDoS attacks on banks
```

### Consultar Investigaciones Anteriores

```
# Ver lista de investigaciones
/runs

# Ver detalles de la investigación #5
/run 5

# Ver los pasos que siguió el sistema
/traces 5
```

### Ejemplos de Uso

**Investigación de amenazas:**
```
/osint APT groups targeting healthcare sector 2024
```

**Análisis de vulnerabilidad:**
```
/osint CVE-2024-3400 exploitation in the wild
```

**Reconocimiento de dominio:**
```
/osint domain reconnaissance example.com
```

**OSINT de username:**
```
/osint find accounts for username "targetuser123"
```

### Configuración Rápida de Telegram

Para habilitar la integración con Telegram (tanto el listener de comandos como la publicación de reportes), sigue estos pasos:

#### 1. Obtener credenciales de Telegram API

1. Ve a [https://my.telegram.org/apps](https://my.telegram.org/apps)
2. Inicia sesión con tu número de teléfono
3. Crea una nueva aplicación (si no tienes una)
4. Copia el `App api_id` y `App api_hash`

#### 2. Configurar variables de entorno

Añade estas variables a tu archivo `.env`:

```env
# Credenciales de Telegram (obligatorio)
TG_APP_ID=12345678
TG_API_HASH=0123456789abcdef0123456789abcdef

# Chat donde publicar reportes y recibir comandos
# Puede ser: nombre del chat, ID numérico, o username (@canal)
TELEGRAM_TARGET_DIALOG=Mi Chat OSINT

# Opcional: intervalo de polling en segundos (default: 10)
TELEGRAM_POLL_INTERVAL=10
```

#### 3. Configurar la sesión (primera vez)

Ejecuta el script de configuración para autenticarte:

```bash
# Con Docker
docker exec -it osint-oa python scripts/setup_telegram.py

# Sin Docker
python scripts/setup_telegram.py
```

El script te pedirá:
1. Tu número de teléfono (con código de país, ej: +34612345678)
2. El código de verificación que recibirás en Telegram
3. (Opcional) Tu contraseña 2FA si la tienes activa

#### 4. Verificar que funciona

```bash
# Ver logs del listener
docker logs osint-oa 2>&1 | grep -i telegram

# Deberías ver:
# INFO - Telegram listener thread started
# INFO - 🤖 Listener active. Press Ctrl+C to stop.
```

Ahora puedes enviar comandos al chat configurado:
- `/osint investigate ransomware attacks` - Iniciar investigación
- `/status` - Ver estado del bot
- `/help` - Ver comandos disponibles

> **Nota**: La sesión se guarda en `data/telegram-session/` y persiste entre reinicios.

### Configuración Avanzada

1. Configura las variables en `.env`:
```env
TELEGRAM_TARGET_DIALOG=nombre_del_chat_o_id
TG_APP_ID=tu_app_id
TG_API_HASH=tu_api_hash
```

2. Inicia la sesión de Telegram:
```bash
./scripts/setup-telegram.sh
```

3. El bot comenzará a escuchar automáticamente al iniciar Docker.

## 🧪 Tests

```bash
# Ejecutar todos los tests
python -m pytest tests/ -v

# Con coverage
python -m pytest tests/ --cov=. --cov-report=html

# Solo smoke tests
python -m pytest tests/test_smoke.py -v

# Sin tests de Telegram (evita conflictos con sesión activa)
python -m pytest tests/ -v --ignore=tests/test_telegram.py
```

> **Nota**: Si el listener de Telegram está activo, algunos tests pueden fallar con "database is locked" debido a que la sesión SQLite de Telethon está en uso. Esto es normal y no indica un problema.

## 📊 Estructura de Datos

### Trace (Traza de Ejecución)
```json
{
  "id": 1,
  "run_id": 5,
  "trace_type": "agent_action",
  "agent_name": "TavilySearchAgent",
  "instruction": "Search for ransomware attacks",
  "evidence_count": 8,
  "confidence_score": 0.85,
  "evidence": {
    "iocs": [
      {"type": "ip", "value": "192.168.1.1", "context": "C2 server"},
      {"type": "domain", "value": "malware.evil.com", "context": "Distribution site"}
    ],
    "entities": [
      {"type": "threat_actor", "name": "LockBit", "context": "Attribution"}
    ],
    "techniques": ["T1566", "T1059.001"]
  },
  "duration_ms": 3500
}
```

### Evidence Output Format
```json
{
  "summary": "Investigation summary",
  "findings": [...],
  "evidence": {
    "iocs": [{"type": "...", "value": "...", "context": "..."}],
    "entities": [{"type": "...", "name": "...", "context": "..."}],
    "techniques": ["T1566", "T1059"]
  },
  "confidence_score": 0.85,
  "sources": ["https://..."]
}
```

## 🛠 Desarrollo

### Añadir un nuevo agente

1. Crear archivo en `agents/osint/`:
```python
from agents.base import LangChainAgent, AgentCapabilities

class MyNewAgent(LangChainAgent):
    def _define_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="MyNewAgent",
            description="Description for the orchestrator",
            tools=["tool1", "tool2"],
            supported_queries=["keyword1", "keyword2"]
        )
    
    def _get_tools(self) -> List[BaseTool]:
        return [Tool1(), Tool2()]
    
    def _get_system_prompt(self) -> str:
        return """Your agent's system prompt with evidence collection instructions..."""
```

2. Registrar en `agents/osint/__init__.py`
3. Añadir tests en `tests/test_agents.py`

### Añadir una nueva herramienta

1. Crear en `tools/`:
```python
class MyTool(BaseTool):
    name: str = "my_tool"
    description: str = "What this tool does"
    
    def _run(self, input: str) -> str:
        # Implementation
        return result
```

## 📚 Documentación Adicional

- [Arquitectura LangChain](docs/LANGCHAIN_ARCHITECTURE.md)
- [Configuración Telegram MCP](docs/TELEGRAM_MCP_SETUP.md)
- [Changelog](CHANGELOG.md)

## 🔒 Seguridad

- Solo busca información **pública y accesible**
- NO intenta acceder a sistemas protegidos
- Respeta robots.txt y rate limits
- Los IOCs extraídos son para análisis defensivo

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para detalles.

## 🙏 Créditos

- [LangChain](https://langchain.com) - Framework de agentes
- [LangGraph](https://github.com/langchain-ai/langgraph) - Orquestación de agentes
- [Tavily](https://tavily.com) - API de búsqueda AI
- [Maigret](https://github.com/soxoj/maigret) - OSINT de usernames
- [BBOT](https://github.com/blacklanternsecurity/bbot) - Reconocimiento de dominios
