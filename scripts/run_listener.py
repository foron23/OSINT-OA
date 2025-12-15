#!/usr/bin/env python3
# =============================================================================
# OSINT Aggregator - Telegram Listener Script
# =============================================================================
"""
Run the Telegram Message Listener service.

This script starts a polling service that monitors a Telegram chat
for incoming messages and triggers OSINT investigations.

Usage:
    python scripts/run_listener.py
    
Environment Variables:
    TELEGRAM_TARGET_DIALOG  - Target dialog ID (e.g., cht[123456])
    TG_APP_ID               - Telegram API ID
    TG_API_HASH             - Telegram API Hash
"""

import asyncio
import logging
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run the Telegram listener service."""
    from integrations.telegram.listener import TelegramListener
    
    target_dialog = os.getenv("TELEGRAM_TARGET_DIALOG", "")
    poll_interval = int(os.getenv("TELEGRAM_POLL_INTERVAL", "10"))
    
    if not target_dialog:
        logger.error("❌ TELEGRAM_TARGET_DIALOG must be set in .env")
        logger.error("   Format: cht[1234567890] for group chats")
        logger.error("   Use /osint list_dialogs to find dialog IDs")
        sys.exit(1)
    
    listener = TelegramListener(
        target_dialog=target_dialog,
        poll_interval=poll_interval
    )
    
    try:
        await listener.start()
    except KeyboardInterrupt:
        logger.info("\n👋 Listener stopped by user")
        listener.stop()


if __name__ == "__main__":
    asyncio.run(main())
