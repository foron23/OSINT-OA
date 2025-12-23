# =============================================================================
# OSINT OA - Integrations Package
# =============================================================================
"""
Integrations with external tools and services.

Modules:
- telegram: Telegram messaging via Telethon (TelethonClient, TelegramListener)
- tool_runner: External CLI tool runners (ReconNg, SpiderFoot)
"""

# Telegram integration (Telethon-based)
from integrations.telegram import (
    TelethonClient,
    TelethonReportPublisher,
    TelegramListener,
    TelegramFormatter,
    get_telegram_client,
    get_telegram_publisher,
    TELETHON_AVAILABLE,
)

# Backward compatibility aliases
TelegramMCPClient = TelethonClient
TelegramReportPublisher = TelethonReportPublisher

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

__all__ = [
    # New Telegram integration (Telethon)
    "TelethonClient",
    "TelethonReportPublisher",
    "TelegramListener",
    "TelegramFormatter",
    "get_telegram_client",
    "get_telegram_publisher",
    "TELETHON_AVAILABLE",
    # Backward compatibility
    "TelegramMCPClient",
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
