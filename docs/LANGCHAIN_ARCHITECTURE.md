# OSINT OA - LangChain Architecture

## Overview

The OSINT OA uses LangChain with the ReAct (Reasoning + Acting) pattern for all agent operations. This provides:

- **Intelligent reasoning**: Agents think through problems step-by-step
- **Tool orchestration**: Agents decide which tools to use based on context
- **Unified architecture**: All agents share the same base implementation
- **MCP integration**: LangChain tools can be exposed via Model Context Protocol

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (HTML/JS)                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Flask API (app.py)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Control Agent (Orchestrator)                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                      Strategist Agent (Planning)                        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                     ┌─────────────────┼─────────────────┐
                     ▼                 ▼                 ▼
            ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
            │  LangChain     │ │  LangChain     │ │  LangChain     │
            │  Agent 1       │ │  Agent 2       │ │  Agent N       │
            │  (ReAct Loop)  │ │  (ReAct Loop)  │ │  (ReAct Loop)  │
            └────────────────┘ └────────────────┘ └────────────────┘
                     │                 │                 │
                     ▼                 ▼                 ▼
            ┌─────────────────────────────────────────────────────┐
            │                  LangChain Tools                     │
            │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
            │  │ TavilySearch │ │ DuckDuckGo   │ │ WebScraper   │ │
            │  └──────────────┘ └──────────────┘ └──────────────┘ │
            │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
            │  │ IOCExtractor │ │ TagExtractor │ │ GoogleDork   │ │
            │  └──────────────┘ └──────────────┘ └──────────────┘ │
            └─────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Validator Agent (QA)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                     ┌─────────────────┼─────────────────┐
                     ▼                 ▼                 ▼
            ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
            │    SQLite      │ │   Telegram     │ │     MCP        │
            │   Database     │ │   Publisher    │ │    Server      │
            └────────────────┘ └────────────────┘ └────────────────┘
```

## File Structure

```
agents/
├── __init__.py              # Package exports
├── langchain_tools.py       # All LangChain tools (13 tools)
├── langchain_agents.py      # All LangChain agents (8 agents)
├── osint_base.py            # Legacy base class (backward compat)
├── strategist_agent.py      # Task planning agent
├── control_agent.py         # Orchestration agent
└── validator_agent.py       # Validation and reporting agent

mcp/
├── __init__.py
└── osint_server.py          # MCP server with LangChain integration
```

## LangChain Tools

All tools inherit from `langchain_core.tools.BaseTool`:

### Search & Scraping Tools

| Tool | Description | API Required |
|------|-------------|--------------|
| `TavilySearchTool` | AI-powered web search | TAVILY_API_KEY |
| `DuckDuckGoSearchTool` | Free web search | None |
| `GoogleDorkBuilderTool` | Advanced Google dorks | None |
| `WebScraperTool` | HTML content extraction | None |

### Analysis Tools

| Tool | Description | API Required |
|------|-------------|--------------|
| `IOCExtractorTool` | Extract IPs, CVEs, hashes | None |
| `TagExtractorTool` | Security tag extraction | None |

### OSINT Tools (Identity & Domain)

| Tool | Description | API Required |
|------|-------------|--------------|
| `MaigretUsernameTool` | Username search across 500+ sites | None |
| `MaigretReportTool` | Generate username OSINT reports | None |
| `BbotSubdomainTool` | Subdomain enumeration | None |
| `BbotWebScanTool` | Web reconnaissance | None |
| `BbotEmailTool` | Email harvesting | None |
| `HoleheEmailTool` | Email registration checker (100+ sites) | None |
| `AmassEnumTool` | OWASP Amass subdomain enum | None |
| `AmassIntelTool` | Organization domain discovery | None |
| `PhoneInfogaScanTool` | Phone number OSINT | None |

### Integration Tools

| Tool | Description | API Required |
|------|-------------|--------------|
| `TelegramPublishTool` | Telegram publishing | TELEGRAM_* |
| `MCPSearchTool` | MCP server integration | None |
| `MCPNormalizeTool` | Item normalization via MCP | None |

### Tool Usage Example

```python
from tools import MaigretUsernameTool, HoleheEmailTool, AmassEnumTool

# Username OSINT
maigret = MaigretUsernameTool()
result = maigret.invoke({"username": "john_doe", "top_sites": 50})

# Email registration check
holehe = HoleheEmailTool()
result = holehe.invoke({"email": "user@example.com"})

# Subdomain enumeration  
amass = AmassEnumTool()
result = amass.invoke({"domain": "example.com", "passive": True})
```

```python
from agents.langchain_tools import TavilySearchTool

tool = TavilySearchTool()
result = tool.invoke({
    "query": "ransomware attacks 2024",
    "max_results": 10
})
```

## LangChain Agents

All agents inherit from `LangChainAgent` and use the ReAct pattern via `langgraph.prebuilt.create_react_agent`:

| Agent | Tools | Use Case |
|-------|-------|----------|
| `TavilySearchAgent` | Tavily, IOC, Tags | Primary OSINT search |
| `DuckDuckGoSearchAgent` | DuckDuckGo, IOC, Tags | Free search fallback |
| `GoogleDorkingAgent` | GoogleDork, WebScraper | Advanced targeted search |
| `WebScraperAgent` | WebScraper, IOC, Tags | Deep content extraction |
| `ThreatIntelAgent` | Tavily, IOC | Threat intelligence |
| `IOCAnalysisAgent` | IOC, Tavily | IOC enrichment |
| `HybridOsintAgent` | All search + analysis | Comprehensive OSINT |
| `ReportGeneratorAgent` | Telegram | Report generation |

### Agent Usage Example

```python
from agents.langchain_agents import TavilySearchAgent, LangChainAgentRegistry

# Get agent
agent = TavilySearchAgent()
# or
agent = LangChainAgentRegistry.get("TavilySearchAgent")

# Check availability
available, message = agent.is_available()

# Run collection
import asyncio

async def collect():
    results = await agent.collect(
        query="APT threat groups",
        limit=10,
        scope="cybersecurity"
    )
    return results

results = asyncio.run(collect())
```

## ReAct Pattern

Each agent follows the ReAct (Reasoning + Acting) loop:

```
1. THINK: Analyze the query and context
2. ACT: Select and execute appropriate tool
3. OBSERVE: Analyze tool output
4. REPEAT: Continue until goal achieved
5. RESPOND: Return structured findings
```

### System Prompt Structure

```python
system_prompt = """You are an expert OSINT analyst agent.

Your name: {agent_name}
Your role: {agent_description}

Available Tools:
- tool_1: description
- tool_2: description

Guidelines:
- Focus on gathering accurate intelligence
- Extract IOCs when found
- Provide source URLs
- Return structured JSON

Output Format:
Return findings as JSON array with:
- title, summary, url, tags, indicators
"""
```

## MCP Integration

The MCP server (`mcp/osint_server.py`) exposes LangChain tools via Model Context Protocol:

### Available MCP Tools

| MCP Tool | LangChain Tool |
|----------|----------------|
| `search_news` | TavilySearchTool / DuckDuckGoSearchTool |
| `normalize_item` | NormalizeItemTool |
| `publish_telegram` | TelegramPublishTool |
| `analyze_content` | AnalyzeContentTool |
| `extract_iocs` | IOCExtractorTool |
| `get_agent_capabilities` | LangChainAgentRegistry |

### Running MCP Server

```bash
python -m mcp.osint_server
```

## Registry Pattern

The `LangChainAgentRegistry` manages all agents:

```python
from agents.langchain_agents import LangChainAgentRegistry

# List all agents
agents = LangChainAgentRegistry.list_agents()

# Get specific agent
agent = LangChainAgentRegistry.get("TavilySearchAgent")

# Get available agents only
available = LangChainAgentRegistry.get_available_agents()

# Get capabilities
caps = LangChainAgentRegistry.get_capabilities()
```

## Environment Variables

Required for full functionality:

```bash
# Required
OPENAI_API_KEY=sk-...          # For GPT models in ReAct loop

# Recommended  
TAVILY_API_KEY=tvly-...        # For TavilySearchAgent

# Optional
TELEGRAM_BOT_TOKEN=...         # For Telegram publishing
TELEGRAM_CHAT_ID=...           # Telegram channel
LANGSMITH_API_KEY=lsv2_...     # For LangSmith tracing
```

## Dependencies

Core LangChain packages:

```
langchain>=1.1.0
langchain-core>=1.2.0
langchain-openai>=1.1.0
langchain-community>=0.4.0
langchain-tavily>=0.2.0
langgraph>=1.0.0
```

## Backward Compatibility

Legacy agent names are aliased for backward compatibility:

```python
# These all work:
from agents import TavilySearchAgent
from agents import TavilySearchOsintAgent  # alias
from agents import LangChainAgentRegistry
from agents import AgentRegistry  # same as above
```

## Investigation Features (v1.4.0+)

### Robust Investigation System

Investigations now support partial completion, allowing results to be returned even when some agents fail.

#### Progress Tracking

```python
from agents.control import InvestigationProgress, AgentResult

# Progress is tracked automatically during investigation
progress = InvestigationProgress(
    run_id=1,
    topic="Ransomware analysis",
    depth="standard",
    started_at=datetime.now()
)

# Each agent result is tracked
progress.add_agent_result(AgentResult(
    agent_name="TavilySearchAgent",
    success=True,
    result="Found 5 articles",
    duration_seconds=2.5,
    iocs_extracted=3
))

# Check if we have useful results despite some failures
if progress.has_useful_results():
    # Generate partial report
    ...
```

#### Investigation Status

| Status | Description |
|--------|-------------|
| `completed` | All requested agents succeeded |
| `partial` | Some agents failed but useful results available |
| `failed` | No useful results could be gathered |

### Agent Selection

Investigations can be run with specific agent selection or auto mode:

```python
from agents.control import ControlAgent

control = ControlAgent()

# Auto mode - agent selects appropriate agents
result = control.investigate(
    topic="APT29 analysis",
    depth="deep"
)

# Manual mode - specify exact agents
result = control.investigate(
    topic="APT29 analysis",
    agents=["TavilySearchAgent", "ThreatIntelAgent", "IOCAnalysisAgent"],
    depth="standard"
)
```

#### Available Agents

| Category | Agents |
|----------|--------|
| **Search** | TavilySearchAgent, DuckDuckGoSearchAgent, GoogleDorkingAgent |
| **Analysis** | WebScraperAgent, ThreatIntelAgent, IOCAnalysisAgent, HybridOsintAgent |
| **Identity** | MaigretAgent, HoleheAgent, PhoneInfogaAgent |
| **Infrastructure** | BbotAgent |
| **Utility** | ReportGeneratorAgent |

### Investigation Continuation

Investigations can be continued from previous runs:

```python
# Continue an investigation with new focus
result = control.investigate(
    topic="APT29 analysis",  # Original topic
    depth="deep",
    continue_from={
        "previous_findings": "Found connections to IP 192.168.1.1",
        "previous_iocs": ["192.168.1.1", "evil-domain.com"],
        "new_instructions": "Focus on the domain infrastructure",
        "original_run_id": 42,
    }
)
```

#### API Endpoint

```http
POST /api/runs/{run_id}/continue

{
  "new_instructions": "Focus on the email addresses found",
  "agents": ["HoleheAgent", "MaigretAgent"],
  "selected_iocs": ["user@example.com", "admin@evil.com"],
  "depth": "standard",
  "publish_telegram": true
}
```

Response:
```json
{
  "run_id": 43,
  "continued_from": 42,
  "status": "completed",
  "partial": false,
  "report": {...},
  "investigation": {...}
}
```

### Partial Report Generation

When investigations fail partially, a report is still generated:

```python
# Example partial report structure
"""
## Partial Investigation Report

**Topic:** Ransomware analysis
**Status:** Partial completion due to errors
**Agents Succeeded:** 3
**Agents Failed:** 2

### Errors Encountered
- BbotAgent: Connection timeout
- MaigretAgent: Command not found

### Collected Findings

#### From TavilySearchAgent
Found important information about...

#### From ThreatIntelAgent
Identified threat actor...

### Evidence Summary
- 5 IP addresses
- 3 domain names
- 2 email addresses

### Recommendations
- Review errors and retry failed agents individually
- Consider using lower depth for more stable results
- Use 'Continue Investigation' to resume with specific agents
"""
```

