# 🔍 OSINT Agentic Operations

**Sistema de Operaciones OSINT Agéntico** - Una plataforma avanzada de inteligencia de código abierto basada en agentes LangChain/LangGraph que colaboran para realizar investigaciones exhaustivas.

[![Tests](https://img.shields.io/badge/tests-108%20passed-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-ReAct-orange)](https://langchain.com)

## 🎯 Descripción

OSINT Agentic Operations es un sistema donde **múltiples agentes especializados colaboran** para realizar investigaciones de inteligencia de código abierto. A diferencia de herramientas tradicionales, este sistema:

- **Colaboración Multi-Agente**: Los agentes trabajan juntos, compartiendo hallazgos y evidencias
- **Extracción Automática de IOCs**: Cada agente extrae y reporta Indicadores de Compromiso
- **Trazabilidad Completa**: Cada acción, decisión y hallazgo queda registrado
- **Integración Telegram**: Recibe comandos y publica reportes automáticamente

## ✨ Características

### 🤖 Sistema de Agentes
- **ControlAgent**: Orquestador que planifica y coordina investigaciones
- **10 agentes especializados**: Búsqueda, scraping, análisis de amenazas, IOCs, OSINT de usernames
- **Patrón ReAct**: Reasoning + Acting con LangGraph
- **Evidencia estructurada**: Todos los agentes extraen IOCs, entidades y técnicas MITRE ATT&CK

### 🔬 Capacidades de Investigación
| Agente | Función | Herramientas |
|--------|---------|--------------|
| TavilySearchAgent | Búsqueda web AI-optimizada | Tavily API |
| DuckDuckGoSearchAgent | Búsqueda privada | DuckDuckGo |
| GoogleDorkingAgent | Búsqueda avanzada | Dork Builder |
| WebScraperAgent | Extracción de contenido | BeautifulSoup |
| ThreatIntelAgent | Inteligencia de amenazas | Multi-tool |
| IOCAnalysisAgent | Análisis de IOCs | IOC Extractor |
| HybridOsintAgent | Investigación completa | All tools |
| MaigretAgent | OSINT de usernames | Maigret (500+ sites) |
| BbotAgent | Reconocimiento de dominios | Bbot |
| ReportGeneratorAgent | Generación de reportes | Templates |

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

OSINT Aggregator incluye un bot de Telegram completo que permite ejecutar investigaciones y consultar resultados directamente desde un chat.

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

### Configuración

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
```

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
