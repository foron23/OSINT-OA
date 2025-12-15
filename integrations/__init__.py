# =============================================================================
# OSINT News Aggregator - Integrations Package
# =============================================================================
"""
Integrations with external tools and services.

Modules:
- telegram: Telegram messaging via MCP (TelegramMCPClient, TelegramListener)
- tool_runner: External CLI tool runners (ReconNg, SpiderFoot)
"""

# Telegram integration (new modular structure)
from integrations.telegram import TelegramMCPClient, TelegramListener

# Legacy imports for backward compatibility
try:
    from integrations.tool_runner import (
        ToolRunner, ReconNgRunner, SpiderFootRunner,
        ExecutionResult, sanitize_argument
    )
except ImportError:
    ToolRunner = None
    ReconNgRunner = None
    SpiderFootRunner = None

try:
    from integrations.telegram_publisher import TelegramPublisher, telegram_publisher
except ImportError:
    TelegramPublisher = None
    telegram_publisher = None

# New Telegram client/publisher
try:
    from integrations.telegram.mcp_client import TelegramReportPublisher
except ImportError:
    TelegramReportPublisher = None

__all__ = [
    # New Telegram integration
    "TelegramMCPClient",
    "TelegramListener",
    "TelegramReportPublisher",
    # Legacy tool runners
    "ToolRunner",
    "ReconNgRunner",
    "SpiderFootRunner",
    "ExecutionResult",
    "sanitize_argument",
    # Legacy telegram
    "TelegramPublisher",
    "telegram_publisher",
]
