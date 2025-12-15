# =============================================================================
# OSINT News Aggregator - Telegram Tools
# =============================================================================
"""
Telegram MCP tools for message publishing.

Provides LangChain tools that interact with Telegram via MCP:
- TelegramMCPSendTool: Send messages to dialogs
- TelegramMCPPublishReportTool: Publish formatted OSINT reports
- TelegramMCPListDialogsTool: List available dialogs
- TelegramPublishTool: Simple publish tool

Uses the juananpe/telegram-mcp fork with send-direct support.
"""

import os
import json
import asyncio
import logging
from typing import Optional, Type

from pydantic import BaseModel, Field

from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun

logger = logging.getLogger(__name__)


# =============================================================================
# Input Schemas
# =============================================================================

class TelegramSendInput(BaseModel):
    """Input for sending Telegram messages."""
    dialog_name: str = Field(description="Target dialog name or ID (e.g., cht[123456] or @username)")
    text: str = Field(description="Message text to send (Markdown supported)")
    send_direct: bool = Field(default=True, description="Send directly (True) or as draft (False)")


class TelegramReportInput(BaseModel):
    """Input for publishing OSINT reports."""
    report: str = Field(description="The OSINT report content in Markdown format")
    query: str = Field(description="The original investigation query")
    dialog_name: Optional[str] = Field(default=None, description="Target dialog (uses default if not specified)")


class TelegramDialogsInput(BaseModel):
    """Input for listing dialogs."""
    only_unread: bool = Field(default=False, description="Show only dialogs with unread messages")


class TelegramSimpleInput(BaseModel):
    """Simple input for Telegram publishing."""
    message: str = Field(description="The message to publish")
    chat_id: Optional[str] = Field(default=None, description="Target chat ID (optional)")


# =============================================================================
# Telegram MCP Send Tool
# =============================================================================

class TelegramMCPSendTool(BaseTool):
    """
    Send messages to Telegram dialogs via MCP.
    
    Uses the telegram-mcp binary with send-direct support.
    """
    
    name: str = "telegram_mcp_send"
    description: str = """Send a message to a Telegram dialog.
    Supports Markdown formatting. Use dialog names like 'cht[123456]' for groups
    or '@username' for users/channels. Set send_direct=True for immediate delivery."""
    args_schema: Type[BaseModel] = TelegramSendInput
    
    def _run(
        self,
        dialog_name: str,
        text: str,
        send_direct: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Send message synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._arun(dialog_name, text, send_direct, run_manager)
                    )
                    return future.result(timeout=60)
            else:
                return loop.run_until_complete(
                    self._arun(dialog_name, text, send_direct, run_manager)
                )
        except RuntimeError:
            return asyncio.run(self._arun(dialog_name, text, send_direct, run_manager))
    
    async def _arun(
        self,
        dialog_name: str,
        text: str,
        send_direct: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Send message asynchronously via MCP."""
        try:
            # Import the MCP client
            from integrations.telegram.mcp_client import TelegramMCPClient
            
            client = TelegramMCPClient()
            
            result = await client.send_message(
                dialog_name=dialog_name,
                text=text,
                send_direct=send_direct
            )
            
            return json.dumps(result)
            
        except ImportError:
            return json.dumps({
                "error": "Telegram MCP client not available",
                "success": False
            })
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return json.dumps({
                "error": str(e),
                "success": False
            })


# =============================================================================
# Telegram MCP Publish Report Tool
# =============================================================================

class TelegramMCPPublishReportTool(BaseTool):
    """
    Publish formatted OSINT reports to Telegram.
    
    Formats the report with headers and metadata before sending.
    """
    
    name: str = "telegram_mcp_publish_report"
    description: str = """Publish a formatted OSINT investigation report to Telegram.
    Automatically formats with headers, timestamps, and query information.
    Uses default dialog from TELEGRAM_TARGET_DIALOG if not specified."""
    args_schema: Type[BaseModel] = TelegramReportInput
    
    def _run(
        self,
        report: str,
        query: str,
        dialog_name: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Publish report synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._arun(report, query, dialog_name, run_manager)
                    )
                    return future.result(timeout=60)
            else:
                return loop.run_until_complete(
                    self._arun(report, query, dialog_name, run_manager)
                )
        except RuntimeError:
            return asyncio.run(self._arun(report, query, dialog_name, run_manager))
    
    async def _arun(
        self,
        report: str,
        query: str,
        dialog_name: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Publish report asynchronously."""
        from datetime import datetime
        
        # Format the report
        formatted = f"""🔍 **OSINT Intelligence Report**
📅 {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
🎯 Query: `{query}`

---

{report}

---
_Generated by OSINT News Aggregator_
"""
        
        # Truncate if too long for Telegram
        if len(formatted) > 4000:
            formatted = formatted[:3950] + "\n\n... _[Report truncated]_"
        
        # Use default dialog if not specified
        target = dialog_name or os.getenv("TELEGRAM_TARGET_DIALOG", "")
        
        if not target:
            return json.dumps({
                "error": "No target dialog specified and TELEGRAM_TARGET_DIALOG not set",
                "success": False
            })
        
        try:
            from integrations.telegram.mcp_client import TelegramMCPClient
            
            client = TelegramMCPClient()
            
            result = await client.send_message(
                dialog_name=target,
                text=formatted,
                send_direct=True
            )
            
            return json.dumps({
                **result,
                "report_length": len(formatted),
                "query": query
            })
            
        except Exception as e:
            logger.error(f"Failed to publish report: {e}")
            return json.dumps({
                "error": str(e),
                "success": False
            })


# =============================================================================
# Telegram MCP List Dialogs Tool
# =============================================================================

class TelegramMCPListDialogsTool(BaseTool):
    """
    List available Telegram dialogs.
    
    Useful for discovering dialog names to use with send tools.
    """
    
    name: str = "telegram_mcp_list_dialogs"
    description: str = """List available Telegram dialogs (chats, groups, channels).
    Shows dialog names, titles, and types.
    Use the 'name' field when sending messages."""
    args_schema: Type[BaseModel] = TelegramDialogsInput
    
    def _run(
        self,
        only_unread: bool = False,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """List dialogs synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._arun(only_unread, run_manager)
                    )
                    return future.result(timeout=60)
            else:
                return loop.run_until_complete(self._arun(only_unread, run_manager))
        except RuntimeError:
            return asyncio.run(self._arun(only_unread, run_manager))
    
    async def _arun(
        self,
        only_unread: bool = False,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """List dialogs asynchronously."""
        try:
            from integrations.telegram.mcp_client import TelegramMCPClient
            
            client = TelegramMCPClient()
            
            dialogs = await client.list_dialogs(only_unread=only_unread)
            
            return json.dumps({
                "count": len(dialogs),
                "dialogs": dialogs
            })
            
        except Exception as e:
            logger.error(f"Failed to list dialogs: {e}")
            return json.dumps({
                "error": str(e),
                "dialogs": []
            })


# =============================================================================
# Simple Telegram Publish Tool (Legacy)
# =============================================================================

class TelegramPublishTool(BaseTool):
    """
    Simple Telegram message publishing tool.
    
    Uses default chat ID from environment if not specified.
    """
    
    name: str = "telegram_publish"
    description: str = """Publish a message to Telegram.
    Uses TELEGRAM_TARGET_DIALOG from environment if chat_id not specified.
    Simple wrapper for quick message sending."""
    args_schema: Type[BaseModel] = TelegramSimpleInput
    
    def _run(
        self,
        message: str,
        chat_id: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Publish message synchronously."""
        target = chat_id or os.getenv("TELEGRAM_TARGET_DIALOG", "")
        
        if not target:
            return json.dumps({
                "success": False,
                "error": "No chat_id specified and TELEGRAM_TARGET_DIALOG not set"
            })
        
        # Use the MCP send tool
        send_tool = TelegramMCPSendTool()
        return send_tool._run(target, message, True, run_manager)
    
    async def _arun(
        self,
        message: str,
        chat_id: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Publish message asynchronously."""
        target = chat_id or os.getenv("TELEGRAM_TARGET_DIALOG", "")
        
        if not target:
            return json.dumps({
                "success": False,
                "error": "No chat_id specified and TELEGRAM_TARGET_DIALOG not set"
            })
        
        send_tool = TelegramMCPSendTool()
        return await send_tool._arun(target, message, True, run_manager)
