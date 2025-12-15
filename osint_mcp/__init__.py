# =============================================================================
# OSINT News Aggregator - MCP Package
# =============================================================================
"""
MCP (Model Context Protocol) server package.
"""

from mcp.osint_server import (
    search_news,
    normalize_item,
    publish_telegram,
    get_agent_capabilities,
    handle_tool_call,
    TOOLS
)

__all__ = [
    "search_news",
    "normalize_item", 
    "publish_telegram",
    "get_agent_capabilities",
    "handle_tool_call",
    "TOOLS"
]
