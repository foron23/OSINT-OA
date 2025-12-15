# OSINT News Aggregator - LangChain Architecture

## Overview

The OSINT News Aggregator uses LangChain with the ReAct (Reasoning + Acting) pattern for all agent operations. This provides:

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

| Tool | Description | API Required |
|------|-------------|--------------|
| `TavilySearchTool` | AI-powered web search | TAVILY_API_KEY |
| `DuckDuckGoSearchTool` | Free web search | None |
| `GoogleDorkBuilderTool` | Advanced Google dorks | None |
| `WebScraperTool` | HTML content extraction | None |
| `IOCExtractorTool` | Extract IPs, CVEs, hashes | None |
| `TagExtractorTool` | Security tag extraction | None |
| `TelegramPublishTool` | Telegram publishing | TELEGRAM_BOT_TOKEN |
| `MCPSearchTool` | MCP server integration | None |
| `MCPNormalizeTool` | Item normalization via MCP | None |

### Tool Usage Example

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
