# =============================================================================
# Telegram Integration Package (Telethon-based)
# =============================================================================
"""
Telegram integration for OSINT OA.

Uses Telethon for direct, robust Telegram integration.

Modules:
- telethon_client: Direct Telegram client using Telethon
- telethon_listener: Real-time message listener with Telethon
- listener: Re-exports TelethonListener as TelegramListener
"""

from integrations.telegram.telethon_client import (
    TelethonClient,
    TelethonReportPublisher,
    TelegramFormatter,
    TelethonConfig,
    get_telegram_client,
    get_telegram_publisher,
    TELETHON_AVAILABLE,
)
from integrations.telegram.telethon_listener import TelethonListener

# Alias for backward compatibility
TelegramListener = TelethonListener
TelegramClient = TelethonClient
ReportPublisher = TelethonReportPublisher

__all__ = [
    "TelethonClient",
    "TelethonReportPublisher",
    "TelethonListener",
    "TelegramListener",
    "TelegramFormatter",
    "TelethonConfig",
    "get_telegram_client",
    "get_telegram_publisher",
    "TelegramClient",
    "ReportPublisher",
    "TELETHON_AVAILABLE",
]
