# Documentación de Desarrollo - OSINT News Aggregator

## 📋 Resumen del Proyecto

Este documento describe el desarrollo de la **estructura base** del OSINT News Aggregator, una aplicación web para agregación de noticias OSINT con arquitectura basada en agentes.

**Actualización v1.3:** Nuevas herramientas OSINT: Holehe, Amass, PhoneInfoga.
**Actualización v1.2:** Migración completa a LangChain ReAct pattern para todos los agentes.
**Actualización v1.1:** Integración con LangChain y Tavily para búsqueda web avanzada.

---

## 🆕 Migración a ReAct Pattern (v1.2)

### Resumen de Cambios

Todos los agentes OSINT ahora utilizan el patrón **ReAct (Reasoning + Acting)** de LangChain/LangGraph:

- ✅ **9 agentes** en AgentRegistry (todos con ReAct)
- ✅ **3 agentes** adicionales en LangChainAgentRegistry
- ✅ **12 agentes totales** funcionando
- ✅ **0 dependencias CLI** - todo basado en APIs web

### Agentes Migrados a ReAct

| Agente | Descripción | Estado |
|--------|-------------|--------|
| `TavilySearchOsintAgent` | Búsqueda principal con Tavily API | ✅ |
| `DuckDuckGoSearchOsintAgent` | Búsqueda fallback sin API key | ✅ |
| `GoogleDorkingOsintAgent` | Google dorking con operadores avanzados | ✅ |
| `WebScraperOsintAgent` | Extracción de contenido de URLs | ✅ |
| `ThreatIntelOsintAgent` | Inteligencia de amenazas | ✅ |
| `ReconNgOsintAgent` | Reconocimiento (web-based) | ✅ |
| `SpiderFootOsintAgent` | OSINT comprensivo (web-based) | ✅ |
| `OsintToolCliAgent` | Recolección genérica (web-based) | ✅ |
| `StandardWebSearchOsintAgent` | Alias compatible con DuckDuckGo | ✅ |

### Arquitectura ReAct

```
┌─────────────────────────────────────────────────────────────┐
│                    ReAct Agent Loop                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1. THINK ────────────────────────────────┐               │
│      └── LLM razona sobre qué información   │               │
│          necesita y qué herramienta usar    │               │
│                                             ▼               │
│   2. ACT ──────────────────────────────────────┐           │
│      └── Ejecuta herramientas (Tavily, DDG,    │           │
│          Web Scraper, IOC Extractor)           │           │
│                                             ▼               │
│   3. OBSERVE ──────────────────────────────────┐           │
│      └── Analiza resultados de las herramientas│           │
│                                             ▼               │
│   4. REPEAT ──────────────────────────────────────┐        │
│      └── Continúa hasta tener suficiente info  │          │
│                                             ▼               │
│   5. RETURN ──────────────────────────────────────         │
│      └── Retorna resultados estructurados                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Cambios en Archivos

| Archivo | Cambios |
|---------|---------|
| `agents/osint_agents.py` | Reescrito con LangChain ReAct pattern |
| `agents/osint_base.py` | Añadido `_extract_tags()`, `_extract_indicators()` |
| `agents/langchain_base.py` | Añadido `LangChainOsintAgent` alias |

### Herramientas (Tools) Disponibles

```python
# Búsqueda
- TavilySearch: Búsqueda web AI-optimizada
- duckduckgo_search: Búsqueda web sin API

# Extracción
- web_scraper: Extracción de contenido de URLs
- ioc_extractor: Extracción de IOCs (IPs, CVEs, hashes)

# Construcción
- google_dork_builder: Constructor de queries avanzadas

# OSINT de Identidad
- MaigretUsernameTool: Búsqueda de usernames en 500+ sitios
- HoleheEmailTool: Verificación de emails en 100+ sitios
- PhoneInfogaScanTool: OSINT de números telefónicos

# OSINT de Dominios
- BbotSubdomainTool: Enumeración de subdominios
- BbotWebScanTool: Reconocimiento web
- BbotEmailTool: Harvesting de emails
- AmassEnumTool: OWASP Amass subdomain enum
- AmassIntelTool: Descubrimiento de dominios de organizaciones
```

### Test de Funcionamiento

```bash
# Verificar agentes disponibles
python -c "
from agents.osint_base import AgentRegistry
for name, agent in AgentRegistry.get_all().items():
    avail, msg = agent.is_available()
    print(f'{'✅' if avail else '❌'} {name}')
"

# Ejecutar demo
python demo.py
```

---

## 🆕 Integración LangChain + Tavily (v1.1)

### Cambios Realizados

Se ha migrado el sistema de agentes para utilizar **LangChain** como framework principal, con **Tavily** como motor de búsqueda web.

#### Nuevos Archivos

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `agents/langchain_base.py` | ~350 | Clase base `LangChainOsintAgent`, registry y capacidades |
| `agents/langchain_agents.py` | ~450 | Agentes especializados: Tavily, Analysis, Hybrid |
| `test_langchain_agents.py` | ~200 | Script de prueba para agentes LangChain |

#### Nuevas Dependencias

```
langchain>=0.1.0
langchain-core>=0.1.0
langchain-openai>=0.0.5
langchain-community>=0.0.10
langchain-tavily>=0.2.0
langgraph>=0.1.0
tavily-python>=0.3.0
```

### Arquitectura de Agentes LangChain

```
┌─────────────────────────────────────────────────────────────┐
│                    LangChain Agent System                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  LangChainOsintAgent (Base)                                 │
│  ├── LLM (ChatOpenAI)                                       │
│  ├── Tools (Tavily, etc.)                                   │
│  └── Methods: collect(), execute_task(), invoke_agent()     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Specialized Agents                      │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐   │   │
│  │  │   Tavily    │ │   Hybrid    │ │  Analysis    │   │   │
│  │  │   Search    │ │   OSINT     │ │    Agent     │   │   │
│  │  │   Agent     │ │   Agent     │ │  (LLM-only)  │   │   │
│  │  └─────────────┘ └─────────────┘ └──────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  LangChainAgentRegistry                                     │
│  └── Manages registration and discovery of agents          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Agentes LangChain Implementados

#### 1. TavilySearchAgent
- **Motor:** Tavily Search API
- **Características:**
  - Búsqueda AI-nativa optimizada para investigación
  - Extracción de contenido raw
  - Resúmenes AI incluidos
  - Scoring de relevancia
- **Uso:** Búsquedas web de noticias y artículos

#### 2. HybridOsintAgent
- **Motor:** Tavily + LLM Analysis
- **Características:**
  - Combina búsqueda con análisis profundo
  - Enriquecimiento de resultados
  - Extracción de indicadores mejorada
- **Uso:** Investigaciones que requieren análisis

#### 3. LangChainAnalysisAgent
- **Motor:** OpenAI GPT
- **Características:**
  - Análisis de contenido proporcionado
  - Clasificación de amenazas
  - Extracción de entidades
  - Scoring de relevancia
- **Uso:** Post-procesamiento de resultados

### Cambios en Archivos Existentes

| Archivo | Cambios |
|---------|---------|
| `config.py` | Añadido: `TAVILY_API_KEY`, `LANGSMITH_*` |
| `agents/__init__.py` | Exporta agentes LangChain |
| `agents/control_agent.py` | `_get_agent()` busca en ambos registros |
| `agents/strategist_agent.py` | Prioriza agentes LangChain en planes |
| `requirements.txt` | Nuevas dependencias LangChain/Tavily |

### Configuración Requerida

```bash
# .env
TAVILY_API_KEY=tvly-your-api-key
OPENAI_API_KEY=sk-your-api-key

# Opcional: LangSmith tracing
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_your-key
LANGSMITH_PROJECT=osint-agents
```

### Pruebas Realizadas

```bash
$ python test_langchain_agents.py

✅ TavilySearchAgent: Agent is available with Tavily search
✅ HybridOsintAgent: Agent is available  
✅ LangChainAnalysisAgent: Agent is available

Testing Tavily Search Agent:
Query: 'cybersecurity ransomware attacks 2024'
✅ Found 5 results
  - AI Summary, Tavily AI
  - Cybersecurity Statistics 2024, Tavily
  - Q4 2024 Travelers' Cyber Threat Report, Tavily
  ...
```

### Integración con Control Agent

El `ControlAgent` ahora busca agentes en este orden:
1. **LangChainAgentRegistry** (Tavily, Analysis, Hybrid)
2. **AgentRegistry** (DuckDuckGo, Google, CLI tools)

```python
def _get_agent(self, name: str):
    # First try LangChain agents (preferred)
    agent = LangChainAgentRegistry.get(name)
    if agent:
        return agent
    # Fall back to legacy agents
    return AgentRegistry.get(name)
```

---

## 🏗️ Arquitectura Implementada

### 1. Visión General

```
┌─────────────────────────────────────────────────────────────────┐
│                        OSINT News Aggregator                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────┐ │
│  │  Frontend   │◄──►│   Flask API  │◄──►│   SQLite Database  │ │
│  │  (SPA)      │    │   (REST)     │    │                    │ │
│  └─────────────┘    └──────────────┘    └────────────────────┘ │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Agent System (Multi-Agent)                  │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │   │
│  │  │   Control    │  │  Strategist  │  │   Validator   │  │   │
│  │  │   Agent      │◄─┤    Agent     │  │    Agent      │  │   │
│  │  └──────┬───────┘  └──────────────┘  └───────────────┘  │   │
│  │         │                                                │   │
│  │         ▼                                                │   │
│  │  ┌───────────────────────────────────────────────────┐  │   │
│  │  │           OSINT Agents (Collectors)               │  │   │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │  │   │
│  │  │  │ WebSearch│ │ Google  │ │ ReconNG │ │SpiderFt │ │  │   │
│  │  │  │  Agent   │ │ Dorking │ │  Agent  │ │  Agent  │ │  │   │
│  │  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ │  │   │
│  │  └───────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│  ┌─────────────────────────┼────────────────────────────────┐  │
│  │                  Integrations                             │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │  │
│  │  │ Tool Runner  │ │  Telegram    │ │    MCP Server    │  │  │
│  │  │ (CLI Tools)  │ │  Publisher   │ │  (Claude Tools)  │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Componentes Principales

| Componente | Archivo(s) | Descripción |
|------------|-----------|-------------|
| **Configuración** | `config.py`, `.env` | Gestión centralizada de configuración |
| **Base de Datos** | `db/sqlite.py`, `db/models.py`, `db/repository.py` | Capa de persistencia SQLite |
| **Agentes** | `agents/*.py` | Sistema multi-agente para OSINT |
| **Integraciones** | `integrations/*.py` | Herramientas externas y Telegram |
| **MCP Server** | `mcp/osint_server.py` | Servidor Model Context Protocol |
| **API REST** | `api/routes.py`, `app.py` | Endpoints Flask |
| **Frontend** | `frontend/*.html/css/js` | Panel de control SPA |

---

## 📂 Estructura de Archivos Creados

### Archivos Raíz

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `config.py` | ~85 | Configuración centralizada con dotenv |
| `app.py` | ~90 | Entrypoint Flask con inicialización |
| `requirements.txt` | ~20 | Dependencias Python |
| `.env.example` | ~25 | Plantilla de variables de entorno |
| `demo.py` | ~130 | Script de demostración |
| `README.md` | ~350 | Documentación del proyecto |

### Módulo `db/` (Base de Datos)

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `__init__.py` | ~32 | Exports del paquete |
| `sqlite.py` | ~256 | Conexión SQLite y schema |
| `models.py` | ~407 | DTOs: Run, Item, Indicator, Tag, Report, OsintResult |
| `repository.py` | ~450 | Repositorios: CRUD para todas las entidades |

**Schema de Base de Datos:**
- `runs` - Investigaciones/ejecuciones
- `sources` - Fuentes de datos
- `items` - Evidencias/noticias OSINT
- `indicators` - IOCs (IP, dominios, hashes, CVEs)
- `tags` - Clasificaciones
- `item_tags` - Relación M:N items-tags
- `item_indicators` - Relación M:N items-indicadores
- `reports` - Reportes generados
- `agent_logs` - Logs de ejecución de agentes

### Módulo `agents/` (Sistema de Agentes)

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `__init__.py` | ~31 | Exports del paquete |
| `osint_base.py` | ~215 | Clase base `OsintAgent`, `AgentCapabilities`, `AgentRegistry` |
| `control_agent.py` | ~324 | Orquestador que coordina investigaciones |
| `strategist_agent.py` | ~280 | Planificador que descompone queries |
| `validator_agent.py` | ~200 | Validador y generador de reportes |
| `osint_agents.py` | ~674 | Agentes especializados de recolección |

**Agentes Implementados:**
1. **StandardWebSearchOsintAgent** - Búsqueda DuckDuckGo
2. **GoogleDorkingOsintAgent** - Google Dorks/Custom Search
3. **ReconNgOsintAgent** - Integración Recon-ng
4. **SpiderFootOsintAgent** - Integración SpiderFoot
5. **OsintToolCliAgent** - Herramientas CLI genéricas

### Módulo `integrations/` (Integraciones)

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `__init__.py` | ~15 | Exports del paquete |
| `tool_runner.py` | ~200 | Ejecutor de herramientas CLI (subfinder, httpx, nmap, nuclei) |
| `telegram_publisher.py` | ~180 | Publicador de mensajes a Telegram |

### Módulo `mcp/` (Model Context Protocol)

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `__init__.py` | ~10 | Exports del paquete |
| `osint_server.py` | ~433 | Servidor MCP con herramientas expuestas |

**Herramientas MCP:**
- `search_news` - Buscar noticias OSINT
- `normalize_item` - Validar/normalizar items
- `publish_telegram` - Publicar a Telegram
- `get_agent_capabilities` - Obtener capacidades de agentes

### Módulo `api/` (API REST)

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `__init__.py` | ~10 | Exports del paquete |
| `routes.py` | ~350 | Endpoints REST completos |

**Endpoints Implementados:**
- `GET /api/health` - Estado del servidor
- `GET /api/agents` - Listar agentes disponibles
- `GET/POST /api/runs` - Gestión de investigaciones
- `GET/DELETE /api/runs/<id>` - Detalle/borrado de run
- `GET/POST /api/items` - Gestión de items
- `GET /api/items/<id>` - Detalle de item
- `GET /api/indicators` - Listar indicadores
- `GET /api/indicators/<id>` - Detalle de indicador
- `GET /api/reports` - Listar reportes
- `GET /api/reports/<id>` - Detalle de reporte
- `POST /api/collect` - Disparar recolección OSINT

### Módulo `frontend/` (Panel Web)

| Archivo | Líneas | Propósito |
|---------|--------|-----------|
| `index.html` | ~200 | Estructura HTML del SPA |
| `styles.css` | ~350 | Estilos CSS modernos |
| `app.js` | ~400 | Lógica JavaScript vanilla |

---

## 🔧 Patrones de Diseño Utilizados

### 1. Repository Pattern
```python
# db/repository.py
class RunRepository:
    @staticmethod
    def create(run: Run) -> int: ...
    @staticmethod
    def get_by_id(id: int) -> Optional[Run]: ...
    @staticmethod
    def list_all(limit: int, offset: int) -> List[Run]: ...
```

### 2. Agent Pattern
```python
# agents/osint_base.py
class OsintAgent(ABC):
    @abstractmethod
    async def collect(self, query: str, limit: int, ...) -> List[OsintResult]: ...
    
    def is_available(self) -> bool: ...
    async def execute_task(self, task: OsintTask) -> OsintTask: ...
```

### 3. Registry Pattern
```python
# agents/osint_base.py
class AgentRegistry:
    _agents: Dict[str, OsintAgent] = {}
    
    @classmethod
    def register(cls, agent: OsintAgent): ...
    @classmethod
    def get_available_agents(cls) -> List[OsintAgent]: ...
```

### 4. Factory Pattern (Implícito)
```python
# app.py
def create_app() -> Flask:
    app = Flask(__name__)
    init_db()
    register_all_agents()
    app.register_blueprint(api_bp)
    return app
```

---

## 🧪 Pruebas Realizadas

### 1. Importación de Módulos ✅
```python
from db import init_db, Database, RunRepository
from agents import ControlAgent, StrategistAgent, ValidatorAgent
from integrations import ToolRunner, TelegramPublisher
```

### 2. Inicialización de Base de Datos ✅
```bash
$ python -c "from db import init_db; init_db()"
# Crea schema en data/osint.db
```

### 3. Demo de Recolección ✅
```bash
$ python demo.py
# Ejecuta recolección con query "cybersecurity ransomware news"
# Resultados: 12 items recolectados de 2 fuentes
```

### 4. API REST ✅
```bash
$ curl http://localhost:5000/api/health
{"status": "ok", "version": "1.0.0", ...}

$ curl http://localhost:5000/api/items?limit=3
{"count": 3, "items": [...]}
```

### 5. Frontend ✅
- Navegación funcionando
- Carga de datos vía API
- Filtros y búsqueda operativos

---

## 🐛 Bugs Corregidos Durante el Desarrollo

### 1. Argumento duplicado en `execute_task`
**Problema:** `collect() got multiple values for keyword argument 'query'`

**Causa:** `**task.inputs` incluía `query` que ya se pasaba explícitamente

**Solución:**
```python
# agents/osint_base.py
extra_kwargs = {k: v for k, v in task.inputs.items() 
              if k not in ("query", "since")}
results = await self.collect(query=query, ..., **extra_kwargs)
```

### 2. sqlite3.Row sin método `.get()`
**Problema:** `'sqlite3.Row' object has no attribute 'get'`

**Causa:** Los objetos `sqlite3.Row` no soportan `.get()` directamente

**Solución:**
```python
# db/models.py - en todos los from_row()
row_dict = dict(row) if hasattr(row, 'keys') else row
return cls(id=row_dict["id"], ...)
```

---

## 📊 Métricas del Proyecto

| Métrica | Valor |
|---------|-------|
| Total de archivos Python | 17 |
| Total de archivos frontend | 3 |
| Líneas de código Python | ~3,500 |
| Líneas de código frontend | ~950 |
| Endpoints API | 18 |
| Herramientas MCP | 4 |
| Agentes OSINT | 5 |
| Tablas en BD | 9 |

---

## 🚀 Próximos Pasos Sugeridos

1. **Agregar más fuentes OSINT:**
   - APIs de threat intelligence (VirusTotal, AbuseIPDB)
   - Feeds RSS de noticias de seguridad
   - Monitoreo de redes sociales

2. **Mejorar el LLM:**
   - Configurar OpenAI API key válida
   - Implementar análisis de sentimiento
   - Generación de resúmenes ejecutivos

3. **Ampliar el frontend:**
   - Gráficas de tendencias
   - Mapa de indicadores geográficos
   - Exportación a PDF/STIX

4. **Seguridad:**
   - Autenticación y autorización
   - Rate limiting
   - Validación estricta de scope

---

## 📝 Notas Finales

Este proyecto implementa la **estructura base completa** según las especificaciones del PROMPT.md. La arquitectura es modular y extensible, permitiendo:

- Agregar nuevos agentes OSINT sin modificar el core
- Extender la API con nuevos endpoints
- Integrar nuevas herramientas CLI
- Escalar horizontalmente los agentes

La aplicación está lista para desarrollo iterativo y pruebas con datos reales.

---

*Documento generado: 2024-12-13*
*Versión: 1.0.0*
