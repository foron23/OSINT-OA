# =============================================================================
# OSINT News Aggregator - MCP Server (LangChain Integrated)
# =============================================================================
"""
Model Context Protocol (MCP) server exposing OSINT tools.

Uses LangChain tools for all OSINT operations:
- search_news: Search for news/OSINT items using Tavily/DuckDuckGo
- normalize_item: Validate and normalize OSINT items
- publish_telegram: Publish report to Telegram
- analyze_content: Deep analysis of content with LLM
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import project modules
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config
from db import init_db
from db.models import OsintResult, ItemType
from db.repository import ItemRepository, SourceRepository
from agents.langchain_agents import LangChainAgentRegistry
from agents.langchain_tools import (
    tavily_search_tool,
    duckduckgo_search_tool,
    normalize_item_tool,
    telegram_publish_tool,
    analyze_content_tool,
    ioc_extractor_tool,
    report_generator_tool
)
from integrations.telegram_publisher import telegram_publisher


# =============================================================================
# MCP Tool Functions
# =============================================================================

async def search_news(
    query: str,
    limit: int = 10,
    since: str = None,
    source: str = None,
    scope: str = None
) -> Dict[str, Any]:
    """
    Search for OSINT news/items using LangChain tools.
    
    Args:
        query: Search query
        limit: Maximum results (default 10)
        since: Filter results from this date (ISO-8601)
        source: Specific source to use (optional)
        scope: Allowed scope for the search
        
    Returns:
        Dictionary with search results
    """
    logger.info(f"search_news called: query='{query}', limit={limit}")
    
    results = []
    errors = []
    
    # Try Tavily first (preferred), then DuckDuckGo
    search_tools = [
        ("Tavily", tavily_search_tool),
        ("DuckDuckGo", duckduckgo_search_tool)
    ]
    
    if source:
        # Filter to specific source if requested
        search_tools = [(n, t) for n, t in search_tools if source.lower() in n.lower()]
    
    for tool_name, search_tool in search_tools:
        try:
            search_results = search_tool.invoke({
                "query": query,
                "max_results": limit
            })
            
            if isinstance(search_results, str):
                search_results = json.loads(search_results) if search_results.strip().startswith('[') else []
            
            for r in search_results:
                if isinstance(r, dict):
                    results.append(r)
            
            if results:
                break  # Got results, stop
                
        except Exception as e:
            errors.append({
                "tool": tool_name,
                "error": str(e)
            })
            logger.error(f"Tool {tool_name} failed: {e}")
    
    return {
        "success": len(results) > 0,
        "query": query,
        "count": len(results),
        "results": results[:limit],
        "errors": errors if errors else None
    }


async def normalize_item(
    title: str,
    summary: str,
    url: str,
    source_name: str = "Manual",
    published_at: str = None,
    tags: List[str] = None,
    indicators: List[Dict] = None
) -> Dict[str, Any]:
    """
    Validate and normalize an OSINT item using LangChain tool.
    
    Args:
        title: Item title
        summary: Item summary/description
        url: Source URL
        source_name: Name of the data source
        published_at: Publication date (ISO-8601)
        tags: List of tags
        indicators: List of IOC dictionaries
        
    Returns:
        Dictionary with normalized item or validation errors
    """
    logger.info(f"normalize_item called: title='{title[:50]}...'")
    
    try:
        result = normalize_item_tool.invoke({
            "title": title,
            "summary": summary,
            "url": url,
            "source_name": source_name,
            "published_at": published_at,
            "tags": tags or [],
            "indicators": indicators or []
        })
        
        if isinstance(result, str):
            result = json.loads(result)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "errors": [{"field": "general", "message": str(e)}]
        }


async def publish_telegram(
    report: str,
    query: str = "OSINT Report",
    stats: Dict = None
) -> Dict[str, Any]:
    """
    Publish an OSINT report to Telegram using LangChain tool.
    
    Args:
        report: Report text in Markdown format
        query: Original query (for context)
        stats: Optional statistics
        
    Returns:
        Dictionary with publish status
    """
    logger.info(f"publish_telegram called: query='{query}'")
    
    try:
        result = telegram_publish_tool.invoke({
            "markdown_report": report,
            "query": query
        })
        
        if isinstance(result, str):
            result = json.loads(result)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "help": "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"
        }


async def analyze_osint_content(
    content: str,
    analysis_type: str = "general"
) -> Dict[str, Any]:
    """
    Analyze OSINT content using LLM (LangChain tool).
    
    Args:
        content: Content to analyze
        analysis_type: Type of analysis (general, threat, sentiment)
        
    Returns:
        Dictionary with analysis results
    """
    logger.info(f"analyze_osint_content called: type='{analysis_type}'")
    
    try:
        result = analyze_content_tool.invoke({
            "content": content,
            "analysis_type": analysis_type
        })
        
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except:
                result = {"analysis": result}
        
        return {"success": True, **result}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


async def extract_iocs(content: str) -> Dict[str, Any]:
    """
    Extract IOCs from content using LangChain tool.
    
    Args:
        content: Content to analyze for IOCs
        
    Returns:
        Dictionary with extracted IOCs
    """
    logger.info(f"extract_iocs called")
    
    try:
        result = ioc_extractor_tool.invoke({"content": content})
        
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except:
                result = {"raw": result}
        
        return {"success": True, "indicators": result}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_agent_capabilities() -> Dict[str, Any]:
    """
    Get capabilities of all registered LangChain OSINT agents.
    
    Returns:
        Dictionary with agent capabilities
    """
    capabilities = LangChainAgentRegistry.get_capabilities()
    
    available_agents = []
    for agent in LangChainAgentRegistry.get_available_agents():
        available_agents.append(agent.name)
    
    return {
        "agents": capabilities,
        "total": len(capabilities),
        "available": available_agents,
        "available_count": len(available_agents)
    }


# =============================================================================
# MCP Server Implementation
# =============================================================================

# Tool definitions for MCP (LangChain integrated)
TOOLS = [
    {
        "name": "search_news",
        "description": "Search for OSINT news and security-related items using Tavily/DuckDuckGo (LangChain)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (keywords, domain, etc.)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default 10)",
                    "default": 10
                },
                "since": {
                    "type": "string",
                    "description": "Only results from this date (ISO-8601 format)"
                },
                "source": {
                    "type": "string",
                    "description": "Specific source to use (Tavily/DuckDuckGo)"
                },
                "scope": {
                    "type": "string",
                    "description": "Allowed scope/domains for the search"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "normalize_item",
        "description": "Validate and normalize an OSINT item using LangChain",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Item title"
                },
                "summary": {
                    "type": "string",
                    "description": "Item summary/description"
                },
                "url": {
                    "type": "string",
                    "description": "Source URL"
                },
                "source_name": {
                    "type": "string",
                    "description": "Name of the data source",
                    "default": "Manual"
                },
                "published_at": {
                    "type": "string",
                    "description": "Publication date (ISO-8601)"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tags"
                },
                "indicators": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of IOC dictionaries"
                }
            },
            "required": ["title", "summary", "url"]
        }
    },
    {
        "name": "publish_telegram",
        "description": "Publish an OSINT report to Telegram using LangChain tool",
        "inputSchema": {
            "type": "object",
            "properties": {
                "report": {
                    "type": "string",
                    "description": "Report text in Markdown format"
                },
                "query": {
                    "type": "string",
                    "description": "Original query (for context)",
                    "default": "OSINT Report"
                },
                "stats": {
                    "type": "object",
                    "description": "Optional statistics"
                }
            },
            "required": ["report"]
        }
    },
    {
        "name": "analyze_content",
        "description": "Analyze OSINT content using LLM for insights, threats, and sentiment",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Content to analyze"
                },
                "analysis_type": {
                    "type": "string",
                    "description": "Type of analysis: general, threat, sentiment",
                    "default": "general"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "extract_iocs",
        "description": "Extract Indicators of Compromise (IOCs) from content",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Content to analyze for IOCs"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "get_agent_capabilities",
        "description": "Get capabilities of all registered LangChain OSINT agents",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]


async def handle_tool_call(name: str, arguments: Dict) -> Any:
    """Handle a tool call from MCP client."""
    
    if name == "search_news":
        return await search_news(**arguments)
    
    elif name == "normalize_item":
        return await normalize_item(**arguments)
    
    elif name == "publish_telegram":
        return await publish_telegram(**arguments)
    
    elif name == "analyze_content":
        return await analyze_osint_content(**arguments)
    
    elif name == "extract_iocs":
        return await extract_iocs(**arguments)
    
    elif name == "get_agent_capabilities":
        return await get_agent_capabilities()
    
    else:
        return {"error": f"Unknown tool: {name}"}


def run_server():
    """Run the MCP server with LangChain integration."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types
        
        server = Server("osint-aggregator-langchain")
        
        @server.list_tools()
        async def list_tools() -> list[types.Tool]:
            """List available tools."""
            return [
                types.Tool(
                    name=tool["name"],
                    description=tool["description"],
                    inputSchema=tool["inputSchema"]
                )
                for tool in TOOLS
            ]
        
        @server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
            """Call a tool with arguments."""
            result = await handle_tool_call(name, arguments)
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
        async def main():
            # Initialize database
            init_db()
            
            # Register LangChain agents
            from agents.langchain_agents import register_all_agents
            register_all_agents()
            
            logger.info("Starting OSINT MCP Server (LangChain)...")
            logger.info(f"Available agents: {LangChainAgentRegistry.list_agents()}")
            
            async with stdio_server() as (read_stream, write_stream):
                await server.run(
                    read_stream,
                    write_stream,
                    server.create_initialization_options()
                )
        
        asyncio.run(main())
        
    except ImportError:
        logger.error("MCP package not installed. Run: pip install mcp")
        print("Error: MCP package not installed.")
        print("Install with: pip install mcp")
        sys.exit(1)


if __name__ == "__main__":
    run_server()
