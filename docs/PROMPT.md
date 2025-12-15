# OSINT News Aggregator

## Project Overview

A comprehensive **Open Source Intelligence (OSINT) News Aggregator** with an **agent-based architecture** using **LangChain** and the **ReAct pattern**. The application collects, analyzes, and distributes cybersecurity intelligence through multiple specialized agents.

## Architecture

```
osint_aggregator/
├── agents/                     # Agent implementations
│   ├── __init__.py            # Package exports
│   ├── base.py                # LangChainAgent base class, AgentCapabilities
│   ├── registry.py            # AgentRegistry for agent discovery
│   ├── control.py             # ControlAgent - investigation orchestrator
│   ├── consolidator.py        # ConsolidatorAgent - Telegram publishing
│   └── osint/                 # OSINT-specialized agents
│       ├── __init__.py
│       ├── search.py          # TavilySearchAgent, DuckDuckGoSearchAgent, GoogleDorkingAgent
│       ├── analysis.py        # WebScraperAgent, ThreatIntelAgent, IOCAnalysisAgent
│       ├── hybrid.py          # HybridOsintAgent
│       ├── report.py          # ReportGeneratorAgent
│       └── osrframework.py    # OSRFrameworkAgent
│
├── tools/                      # LangChain tools
│   ├── __init__.py            # Package exports
│   ├── base.py                # ToolResult dataclass
│   ├── search.py              # TavilySearchTool, DuckDuckGoSearchTool
│   ├── scraping.py            # WebScraperTool, GoogleDorkBuilderTool
│   ├── analysis.py            # IOCExtractorTool, TagExtractorTool
│   ├── osrframework.py        # Usufy, Mailfy, Domainfy, Searchfy, Phonefy tools
│   └── telegram.py            # TelegramMCPSendTool, TelegramMCPPublishReportTool
│
├── config/                     # Configuration management
│   ├── __init__.py
│   └── settings.py            # Settings class with environment validation
│
├── integrations/              # External service integrations
│   ├── __init__.py
│   └── telegram/              # Telegram MCP integration
│       ├── __init__.py
│       ├── mcp_client.py      # TelegramMCPClient, TelegramReportPublisher
│       └── listener.py        # TelegramListener for incoming messages
│
├── db/                        # Database layer
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy models
│   └── database.py            # Database initialization
│
├── api/                       # API endpoints
│   └── routes.py              # Flask blueprint
│
├── scripts/                   # Utility scripts
│   ├── run_listener.py        # Start Telegram listener service
│   └── demo.py                # Interactive demo script
│
├── bin/                       # External binaries
│   └── telegram-mcp           # Telegram MCP server (juananpe fork)
│
├── data/                      # Data storage
│   └── osint.db              # SQLite database
│
├── templates/                 # HTML templates
│   └── index.html            # Frontend
│
├── static/                    # Static assets
│   ├── css/
│   └── js/
│
├── app.py                     # Flask application entry point
├── requirements.txt           # Python dependencies
├── .env                       # Environment configuration
└── PROMPT.md                  # This file
```

---

## Core Components

### 1. Agents (`agents/`)

All agents extend `LangChainAgent` and use the **ReAct (Reasoning + Acting)** pattern for intelligent task execution.

#### Base Classes (`agents/base.py`)

```python
@dataclass
class AgentCapabilities:
    """Describes what an agent can do."""
    name: str                    # Unique agent name
    description: str             # Human-readable description
    tools: List[str]             # List of tool names
    supported_queries: List[str] # Query types agent handles
    requires_api_keys: List[str] # Required environment variables

class LangChainAgent(ABC):
    """Abstract base class for all LangChain agents."""
    
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    @abstractmethod
    def capabilities(self) -> AgentCapabilities: ...
    
    @abstractmethod
    def get_tools(self) -> List[BaseTool]: ...
    
    def run(self, query: str) -> str:
        """Execute a query using the ReAct pattern."""
        ...
    
    def is_available(self) -> Tuple[bool, str]:
        """Check if agent can run (API keys present, etc.)."""
        ...
```

#### Agent Registry (`agents/registry.py`)

Centralized registry for discovering and accessing agents.

```python
class AgentRegistry:
    @classmethod
    def get(cls, name: str) -> Optional[LangChainAgent]:
        """Get agent by name."""
        ...
    
    @classmethod
    def list_all(cls) -> List[str]:
        """List all registered agent names."""
        ...
    
    @classmethod
    def list_available(cls) -> List[Dict[str, Any]]:
        """List agents with availability status."""
        ...
    
    @classmethod
    def get_by_capability(cls, query_type: str) -> List[LangChainAgent]:
        """Get agents supporting a specific query type."""
        ...
```

#### OSINT Agents (`agents/osint/`)

| Agent | Purpose | Tools Used |
|-------|---------|------------|
| `TavilySearchAgent` | AI-optimized web search | `tavily_search` |
| `DuckDuckGoSearchAgent` | Privacy-focused search | `duckduckgo_search` |
| `GoogleDorkingAgent` | Advanced search operators | `google_dork_builder`, `duckduckgo_search` |
| `WebScraperAgent` | Web page content extraction | `web_scraper` |
| `ThreatIntelAgent` | Threat intelligence analysis | `tavily_search`, `ioc_extractor`, `tag_extractor` |
| `IOCAnalysisAgent` | IOC extraction and research | `ioc_extractor`, `duckduckgo_search`, `web_scraper` |
| `HybridOsintAgent` | Multi-tool comprehensive analysis | All search/analysis tools |
| `ReportGeneratorAgent` | Intelligence report formatting | `tag_extractor` |
| `OSRFrameworkAgent` | Identity/username research | `usufy`, `mailfy`, `domainfy`, `searchfy`, `phonefy` |

#### Control Agents

| Agent | Purpose |
|-------|---------|
| `ControlAgent` | Orchestrates multi-agent investigations |
| `ConsolidatorAgent` | Publishes reports to Telegram |

---

### 2. Tools (`tools/`)

LangChain-compatible tools providing OSINT capabilities.

#### Search Tools (`tools/search.py`)
- `TavilySearchTool`: Tavily AI search API
- `DuckDuckGoSearchTool`: DuckDuckGo web search

#### Scraping Tools (`tools/scraping.py`)
- `WebScraperTool`: Extract text content from URLs
- `GoogleDorkBuilderTool`: Build Google dork queries

#### Analysis Tools (`tools/analysis.py`)
- `IOCExtractorTool`: Extract IPs, domains, hashes, CVEs, emails
- `TagExtractorTool`: Extract entities and classification tags

#### OSRFramework Tools (`tools/osrframework.py`)
- `UsufyTool`: Username enumeration across platforms
- `MailfyTool`: Email verification and account discovery
- `DomainfyTool`: Domain availability and research
- `SearchfyTool`: General identity search
- `PhonefyTool`: Phone number lookup

#### Telegram Tools (`tools/telegram.py`)
- `TelegramMCPSendTool`: Send messages via MCP
- `TelegramMCPPublishReportTool`: Publish formatted OSINT reports
- `TelegramMCPListDialogsTool`: List available Telegram dialogs

---

### 3. Telegram Integration (`integrations/telegram/`)

#### MCP Client (`mcp_client.py`)

Uses the **juananpe/telegram-mcp** fork with `send: true` support for direct message delivery.

```python
class TelegramMCPClient:
    """Client for Telegram MCP server."""
    
    async def send_message(
        self,
        dialog_name: str,
        text: str,
        send_direct: bool = True  # True = send, False = draft
    ) -> Dict[str, Any]: ...
    
    async def list_dialogs(self, only_unread: bool = False) -> List[Dict]: ...
    
    async def get_dialog_messages(self, dialog_name: str) -> Dict: ...
    
    async def mark_as_read(self, dialog_name: str) -> Dict: ...

class TelegramReportPublisher:
    """High-level OSINT report publisher."""
    
    async def publish_report(
        self,
        report_markdown: str,
        query: str,
        stats: Dict = None
    ) -> Dict[str, Any]: ...
```

#### Message Listener (`listener.py`)

Polling-based service for monitoring incoming Telegram messages and triggering investigations.

```python
class TelegramListener:
    """Polls Telegram for incoming messages."""
    
    async def start(self) -> None:
        """Start the polling loop."""
        ...
    
    def add_handler(self, handler: MessageHandler) -> None:
        """Add custom message handler."""
        ...
    
    def set_investigation_callback(self, callback: Callable) -> None:
        """Set callback for running investigations."""
        ...
```

**Supported Commands:**
| Command | Description |
|---------|-------------|
| `/osint <query>` | Start full OSINT investigation |
| `/search <query>` | Quick search |
| `/status` | Show bot status |
| `/help` | Show help message |

**Natural Language Detection:**
The listener also recognizes keywords like "investiga", "busca", "analyze", "threat intel", etc.

---

### 4. Configuration (`config/`)

Centralized configuration management with environment variable validation.

```python
@dataclass
class Settings:
    # Flask
    DEBUG: bool = False
    SECRET_KEY: str = "dev-secret"
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    DEFAULT_MODEL: str = "gpt-4o-mini"
    
    # Tavily
    TAVILY_API_KEY: str = ""
    
    # Telegram MCP
    TG_APP_ID: str = ""
    TG_API_HASH: str = ""
    TELEGRAM_TARGET_DIALOG: str = ""
    
    # LangSmith (optional)
    LANGSMITH_TRACING: bool = False
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "osint-aggregator"
```

---

## Environment Variables

Create a `.env` file with:

```bash
# Required for agents
OPENAI_API_KEY=sk-proj-...
TAVILY_API_KEY=tvly-...

# Telegram (for publishing)
TG_APP_ID=12345678
TG_API_HASH=abcdef1234567890...
TELEGRAM_TARGET_DIALOG=cht[1234567890]

# Optional: LangSmith tracing
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=ls-...
LANGSMITH_PROJECT=osint-aggregator

# Flask (optional)
FLASK_DEBUG=false
SECRET_KEY=your-secret-key
```

---

## Usage

### Start Flask API

```bash
cd /home/ubuntu/Desktop/AgentesIA/ProyectoFinal
source venv/bin/activate
python app.py
```

Server runs at http://localhost:5000

### Start Telegram Listener

```bash
python scripts/run_listener.py
```

Or directly:

```bash
python -m integrations.telegram.listener
```

### Interactive Demo

```bash
python scripts/demo.py                              # Interactive mode
python scripts/demo.py --list                       # List all agents
python scripts/demo.py TavilySearchAgent "APT29"    # Run specific agent
python scripts/demo.py --investigate "ransomware"   # Full investigation
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Frontend HTML |
| GET | `/api/items` | List OSINT items |
| GET | `/api/items/<id>` | Get item by ID |
| POST | `/api/search` | Execute search query |
| POST | `/api/investigate` | Start full investigation |
| GET | `/api/agents` | List available agents |
| POST | `/api/agents/<name>/run` | Run specific agent |
| GET | `/api/runs` | List investigation runs |
| GET | `/api/runs/<id>` | Get run details |
| GET | `/api/reports` | List reports |
| GET | `/api/reports/<id>` | Get report by ID |

---

## Agent Workflow

```
User Request (API / Telegram)
    │
    ▼
┌─────────────────┐
│  ControlAgent   │  ◄── Orchestrates investigation, plans strategy
└────────┬────────┘
         │
         │ delegate_to_agent()
    ┌────┴────┬────────┬────────┐
    ▼         ▼        ▼        ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│Tavily │ │DuckGo │ │WebScr │ │IOC    │  ◄── OSINT specialists
│Search │ │Search │ │Agent  │ │Agent  │      (run in parallel)
└───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
    │         │        │        │
    └─────────┴────────┴────────┘
                │
                ▼
    ┌─────────────────┐
    │  Consolidation  │  ◄── Merge and deduplicate results
    └────────┬────────┘
             ▼
    ┌─────────────────┐
    │ConsolidatorAgent│  ◄── Format and publish to Telegram
    └─────────────────┘
             │
             ▼
    📱 Telegram Channel
```

---

## Telegram MCP Integration

### Fork Details

This project uses a modified fork of `@chaindead/telegram-mcp`:

| | Original | Fork |
|---|----------|------|
| **Repository** | @chaindead/telegram-mcp | github.com/juananpe/telegram-mcp/tree/pr-2 |
| **Send Mode** | Draft only | Direct send (`send: true`) |
| **Binary Location** | N/A | `bin/telegram-mcp` |

### Message Flow

```
┌─────────────────┐     tg_send(send:true)     ┌─────────────────┐
│  TelegramMCP    │ ─────────────────────────► │   Telegram      │
│  Client         │                            │   API           │
└─────────────────┘                            └─────────────────┘
        │
        │ Uses local binary
        ▼
┌─────────────────┐
│ bin/telegram-mcp│  ◄── Fork with send-direct support
└─────────────────┘
```

---

## Database Schema

```sql
-- Investigation runs
CREATE TABLE runs (
    id INTEGER PRIMARY KEY,
    query TEXT NOT NULL,
    status TEXT NOT NULL,  -- started|completed|failed|partial
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    stats_json TEXT
);

-- OSINT Items
CREATE TABLE items (
    id INTEGER PRIMARY KEY,
    run_id INTEGER REFERENCES runs(id),
    source TEXT,
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT,
    published_at TEXT,
    item_type TEXT,
    tags TEXT,    -- JSON array
    iocs TEXT,    -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indicators of Compromise
CREATE TABLE indicators (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,   -- ip|domain|url|hash|email|cve
    value TEXT NOT NULL,
    confidence REAL,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(type, value)
);

-- Reports
CREATE TABLE reports (
    id INTEGER PRIMARY KEY,
    run_id INTEGER REFERENCES runs(id),
    query TEXT,
    report TEXT NOT NULL,
    telegram_sent BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Development Guide

### Adding a New Agent

1. **Create agent class** in `agents/osint/`:

```python
from agents.base import LangChainAgent, AgentCapabilities
from tools.search import TavilySearchTool

class MyNewAgent(LangChainAgent):
    @property
    def name(self) -> str:
        return "MyNewAgent"
    
    @property
    def capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="MyNewAgent",
            description="Does something useful",
            tools=["tavily_search"],
            supported_queries=["my_query_type"],
            requires_api_keys=["TAVILY_API_KEY"],
        )
    
    def get_tools(self) -> List[BaseTool]:
        return [TavilySearchTool()]
    
    def _get_system_prompt(self) -> str:
        return """You are an expert at..."""
```

2. **Export from package** - Add to `agents/osint/__init__.py`

3. **Register agent** - Add to `register_all_agents()` in `agents/registry.py`

### Adding a New Tool

1. **Create tool** in `tools/`:

```python
from langchain_core.tools import tool

@tool
def my_tool(query: str) -> str:
    """
    Brief description for the LLM.
    
    Args:
        query: What to search for
        
    Returns:
        Search results
    """
    # Your implementation
    return results
```

2. **Export from package** - Add to `tools/__init__.py`

---

## Dependencies

Key packages in `requirements.txt`:

```
# LangChain stack
langchain==1.1.3
langchain-core==1.2.0
langchain-openai==1.1.3
langgraph==1.0.5

# Flask
flask==3.1.2
flask-cors==5.0.0

# Search tools
tavily-python
duckduckgo-search

# Web scraping
beautifulsoup4
requests

# MCP client
mcp

# Utilities
python-dotenv
```

Install:

```bash
pip install -r requirements.txt
```

---

## Quick Start

```bash
# 1. Clone and setup
cd /home/ubuntu/Desktop/AgentesIA/ProyectoFinal
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run the API
python app.py

# 4. (Optional) Start Telegram listener
python scripts/run_listener.py
```

---

## License

MIT License
