# =============================================================================
# Telegram Integration Package
# =============================================================================
"""
Telegram integration for OSINT News Aggregator.

Modules:
- mcp_client: Telegram MCP client for sending messages
- listener: Polling service for incoming messages
"""

from integrations.telegram.mcp_client import TelegramMCPClient
from integrations.telegram.listener import TelegramListener

__all__ = [
    "TelegramMCPClient",
    "TelegramListener",
]
