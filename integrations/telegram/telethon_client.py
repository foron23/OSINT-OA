# =============================================================================
# Telegram Telethon Client - Direct Integration
# =============================================================================
"""
Direct Telegram integration using Telethon library.

- No external binary dependency (telegram-mcp Go binary)
- Better error handling and reconnection logic
- Native async support
- Full control over formatting (HTML/MarkdownV2)
- Session persistence within Python
- Easier Docker deployment

Usage:
    client = TelethonClient()
    await client.connect()
    await client.send_message(chat_id, "Hello!", parse_mode="html")
"""

import asyncio
import logging
import os
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

logger = logging.getLogger(__name__)

# Telethon imports with graceful fallback
try:
    from telethon import TelegramClient, events
    from telethon.tl.types import (
        Message, User, Chat, Channel,
        PeerUser, PeerChat, PeerChannel,
        InputPeerUser, InputPeerChat, InputPeerChannel,
    )
    from telethon.errors import (
        SessionPasswordNeededError,
        FloodWaitError,
        ChatWriteForbiddenError,
        UserNotParticipantError,
        ChannelPrivateError,
    )
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    logger.warning("Telethon not installed. Install with: pip install telethon")


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class TelethonConfig:
    """Configuration for Telethon client."""
    api_id: int
    api_hash: str
    session_path: str = ""
    session_name: str = "osint_bot"
    system_version: str = "OSINT-OA 1.0"
    device_model: str = "OSINT Agent"
    app_version: str = "1.0"
    flood_sleep_threshold: int = 60
    
    @classmethod
    def from_env(cls) -> "TelethonConfig":
        """Create config from environment variables."""
        api_id_str = os.getenv("TG_APP_ID", os.getenv("TELEGRAM_APP_ID", ""))
        api_hash = os.getenv("TG_API_HASH", os.getenv("TELEGRAM_API_HASH", ""))
        
        if not api_id_str or not api_hash:
            raise ValueError(
                "Telegram credentials not configured. "
                "Set TG_APP_ID and TG_API_HASH environment variables."
            )
        
        try:
            api_id = int(api_id_str)
        except ValueError:
            raise ValueError(f"TG_APP_ID must be an integer, got: {api_id_str}")
        
        # Session path - default to data directory
        session_path = os.getenv(
            "TELEGRAM_SESSION_PATH",
            os.getenv("TG_SESSION_PATH", "/app/data/telegram-session")
        )
        
        # Ensure directory exists
        Path(session_path).mkdir(parents=True, exist_ok=True)
        
        return cls(
            api_id=api_id,
            api_hash=api_hash,
            session_path=session_path,
        )
    
    @property
    def session_file(self) -> str:
        """Full path to session file."""
        return os.path.join(self.session_path, self.session_name)
    
    @property
    def is_valid(self) -> bool:
        """Check if config is valid."""
        return bool(self.api_id and self.api_hash)


# =============================================================================
# Message Formatting - Improved Telegram Formatting
# =============================================================================

class TelegramFormatter:
    """
    Formatter for Telegram messages with HTML support.
    
    Uses HTML parse mode for better compatibility and cleaner output
    compared to Markdown which has escaping issues.
    """
    
    # Telegram message limits
    MAX_MESSAGE_LENGTH = 4096
    MAX_CAPTION_LENGTH = 1024
    
    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML special characters."""
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
    
    @staticmethod
    def format_osint_report(
        report: str,
        query: str,
        run_id: Optional[int] = None,
        stats: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Format an OSINT report for Telegram with rich HTML formatting.
        
        Creates a visually appealing message with:
        - Clear header with emojis
        - Structured sections
        - Highlighted IOCs
        - Statistics if available
        
        Args:
            report: The report content (may be markdown)
            query: The investigation query
            run_id: Optional run identifier
            stats: Optional statistics dict
            
        Returns:
            HTML-formatted message for Telegram
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
        
        # Build header
        header = f"""🔍 <b>OSINT INTELLIGENCE REPORT</b>

<b>📋 Query:</b> <code>{TelegramFormatter.escape_html(query)}</code>
<b>🕐 Date:</b> {timestamp}"""
        
        if run_id:
            header += f"\n<b>🆔 Run:</b> #{run_id}"
        
        header += "\n" + "━" * 28 + "\n"
        
        # Build statistics section
        stats_section = ""
        if stats:
            total = stats.get('total_iocs', stats.get('total_results', 0))
            sources = stats.get('sources_used', [])
            duration = stats.get('duration_seconds', 0)
            
            # Determine status indicator
            if total == 0:
                indicator = "⚪"
                status = "No IOCs found"
            elif total < 5:
                indicator = "🟢"
                status = "Low exposure"
            elif total < 15:
                indicator = "🟡"
                status = "Moderate exposure"
            else:
                indicator = "🔴"
                status = "High exposure"
            
            stats_section = f"""
<b>📊 STATISTICS</b>
├─ {indicator} <b>Status:</b> {status}
├─ 📈 <b>IOCs Found:</b> {total}
├─ 🔌 <b>Sources:</b> {', '.join(sources) if sources else 'Multiple agents'}
└─ ⏱️ <b>Duration:</b> {duration:.1f}s

"""
        
        # Convert markdown report to HTML
        formatted_report = TelegramFormatter.markdown_to_html(report)
        formatted_report = TelegramFormatter.enhance_osint_formatting(formatted_report)
        
        # Build footer
        footer = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 <i>Generated by OSINT OA</i>
🔗 <i>Powered by LangChain + Multi-Agent System</i>"""
        
        full_message = header + stats_section + formatted_report + footer
        
        # Truncate if needed
        if len(full_message) > TelegramFormatter.MAX_MESSAGE_LENGTH - 100:
            return TelegramFormatter.smart_truncate(
                full_message, 
                TelegramFormatter.MAX_MESSAGE_LENGTH - 150
            ) + "\n\n⚠️ <i>[Report truncated - see full report in web interface]</i>" + footer
        
        return full_message
    
    @staticmethod
    def markdown_to_html(text: str) -> str:
        """
        Convert common markdown to Telegram HTML.
        
        Handles:
        - Headers (# ## ###)
        - Bold (**text**)
        - Italic (*text*)
        - Code (`text`)
        - Code blocks (```code```)
        - Links [text](url)
        """
        import re
        
        # Escape existing HTML first
        text = TelegramFormatter.escape_html(text)
        
        # Code blocks (before other transformations)
        text = re.sub(
            r'```(\w*)\n?(.*?)```',
            r'<pre>\2</pre>',
            text,
            flags=re.DOTALL
        )
        
        # Inline code
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        
        # Headers
        text = re.sub(r'^###\s+(.+)$', r'<b>▸ \1</b>', text, flags=re.MULTILINE)
        text = re.sub(r'^##\s+(.+)$', r'\n<b>📌 \1</b>\n', text, flags=re.MULTILINE)
        text = re.sub(r'^#\s+(.+)$', r'\n<b>🔷 \1</b>\n', text, flags=re.MULTILINE)
        
        # Bold (** or __)
        text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__([^_]+)__', r'<b>\1</b>', text)
        
        # Italic (* or _) - be careful not to match ** or __
        text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', text)
        text = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'<i>\1</i>', text)
        
        # Links [text](url) -> text (url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (<code>\2</code>)', text)
        
        # Tables (simplified - convert to list)
        text = re.sub(r'\|[^\n]+\|', lambda m: TelegramFormatter._table_row_to_text(m.group()), text)
        
        return text
    
    @staticmethod
    def _table_row_to_text(row: str) -> str:
        """Convert a markdown table row to plain text."""
        cells = [c.strip() for c in row.strip('|').split('|')]
        if all(c.replace('-', '') == '' for c in cells):
            return ""  # Separator row
        return " │ ".join(cells)
    
    @staticmethod
    def enhance_osint_formatting(text: str) -> str:
        """
        Enhance OSINT report with visual indicators.
        
        Adds emojis and formatting to common OSINT sections and IOCs.
        """
        import re
        
        # Section header mappings
        section_replacements = {
            r'SUBDOMAIN[S]?': '🌐 <b>SUBDOMAINS</b>',
            r'PROFILE[S]?|ACCOUNT[S]?': '👤 <b>PROFILES FOUND</b>',
            r'EMAIL[S]?': '📧 <b>EMAIL ADDRESSES</b>',
            r'TECHNOLOG(Y|IES)': '⚙️ <b>TECHNOLOGIES</b>',
            r'DNS RECORD[S]?': '🔗 <b>DNS RECORDS</b>',
            r'VULNERABILIT(Y|IES)': '⚠️ <b>VULNERABILITIES</b>',
            r'SUMMARY|CONCLUSION': '📋 <b>SUMMARY</b>',
            r'RECOMMENDATION[S]?': '💡 <b>RECOMMENDATIONS</b>',
            r'FINDING[S]?': '🔎 <b>FINDINGS</b>',
            r'SOCIAL MEDIA': '📱 <b>SOCIAL MEDIA</b>',
            r'SOURCE[S]?': '📚 <b>SOURCES</b>',
            r'IOC[S]?|INDICATOR[S]?': '🎯 <b>INDICATORS OF COMPROMISE</b>',
            r'THREAT ACTOR[S]?': '👹 <b>THREAT ACTORS</b>',
            r'MITRE|ATT&amp;CK': '🗺️ <b>MITRE ATT&CK</b>',
        }
        
        for pattern, replacement in section_replacements.items():
            text = re.sub(
                rf'<b>([^<]*{pattern}[^<]*)</b>',
                replacement,
                text,
                flags=re.IGNORECASE
            )
        
        # Highlight IOC types
        ioc_patterns = [
            (r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', r'<code>🔹 \1</code>'),  # IPs
            (r'\b([a-fA-F0-9]{32})\b', r'<code>🔸 \1</code>'),  # MD5
            (r'\b([a-fA-F0-9]{64})\b', r'<code>🔸 \1</code>'),  # SHA256
            (r'\b(CVE-\d{4}-\d{4,7})\b', r'<code>🔴 \1</code>'),  # CVEs
        ]
        
        for pattern, replacement in ioc_patterns:
            text = re.sub(pattern, replacement, text)
        
        # Highlight warnings
        warning_words = ['exposed', 'vulnerable', 'critical', 'leaked', 'sensitive', 'danger']
        for word in warning_words:
            text = re.sub(
                rf'\b({word})\b',
                r'⚠️ <b>\1</b>',
                text,
                flags=re.IGNORECASE
            )
        
        # Format list items
        text = re.sub(r'^[-•]\s+', '  • ', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+\.\s+', '  ▸ ', text, flags=re.MULTILINE)
        
        return text
    
    @staticmethod
    def smart_truncate(text: str, max_length: int) -> str:
        """Truncate text at natural boundaries."""
        if len(text) <= max_length:
            return text
        
        truncated = text[:max_length]
        
        # Try to break at paragraph
        last_para = truncated.rfind('\n\n')
        if last_para > max_length * 0.7:
            return truncated[:last_para]
        
        # Try to break at newline
        last_newline = truncated.rfind('\n')
        if last_newline > max_length * 0.8:
            return truncated[:last_newline]
        
        # Break at last space
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.9:
            return truncated[:last_space]
        
        return truncated
    
    @staticmethod
    def format_status_message(
        agents_available: int,
        agents_total: int,
        version: str = "1.0.0"
    ) -> str:
        """Format a status message."""
        return f"""📊 <b>OSINT Bot Status</b>

✅ <b>Status:</b> Online and listening
🤖 <b>Agents:</b> {agents_available}/{agents_total} available
📦 <b>Version:</b> {version}
📅 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}

<i>Send /help to see available commands.</i>"""
    
    @staticmethod
    def format_help_message() -> str:
        """Format the help message."""
        return """🔍 <b>OSINT Bot - Help</b>

<b>📋 Investigation Commands:</b>
  • <code>/osint &lt;query&gt;</code> - Start OSINT investigation
  • <code>/search &lt;query&gt;</code> - Quick search
  • <code>/deep &lt;query&gt;</code> - Deep investigation (multi-pass)

<b>📊 Results Commands:</b>
  • <code>/runs</code> - List recent investigations
  • <code>/run &lt;id&gt;</code> - View investigation details
  • <code>/traces &lt;id&gt;</code> - View execution traces

<b>⚙️ System Commands:</b>
  • <code>/status</code> - Bot status
  • <code>/help</code> - This help message

<b>📝 Examples:</b>
  • <code>/osint ransomware group LockBit</code>
  • <code>/deep APT29 infrastructure 2024</code>
  • <code>/search CVE-2024-1234</code>

<i>You can also use natural language requests like "investiga sobre..."</i>"""


# =============================================================================
# Telethon Client
# =============================================================================

# Global singleton instance
_telethon_client_instance: Optional['TelethonClient'] = None
_telethon_client_lock = threading.Lock()
_telethon_connect_lock = threading.Lock()


class TelethonClient:
    """
    Direct Telegram client using Telethon.
    
    Provides robust message sending, receiving, and session management.
    """
    
    def __init__(self, config: Optional[TelethonConfig] = None):
        """
        Initialize the Telethon client.
        
        Args:
            config: Configuration, or load from environment
        """
        if not TELETHON_AVAILABLE:
            raise ImportError(
                "Telethon is required for direct Telegram integration. "
                "Install with: pip install telethon"
            )
        
        self.config = config or TelethonConfig.from_env()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.formatter = TelegramFormatter()
        
        # Initialize client
        self._client: Optional[TelegramClient] = None
        self._connected = False
        self._dialogs_cache: Dict[str, Any] = {}
        
        # Target dialog from environment
        self._target_dialog = os.getenv("TELEGRAM_TARGET_DIALOG", "")
    
    @property
    def is_configured(self) -> bool:
        """Check if Telegram is configured."""
        return self.config.is_valid
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected and self._client is not None
    
    async def connect(self) -> bool:
        """
        Connect to Telegram and authenticate.
        
        Uses lock to prevent multiple simultaneous connections to the same session.
        
        Returns:
            True if connected successfully
        """
        # Quick check without lock
        if self._connected and self._client:
            return True
        
        # Acquire threading lock to prevent race conditions across threads
        with _telethon_connect_lock:
            # Re-check after acquiring lock
            if self._connected and self._client:
                return True
            
            try:
                self.logger.info(f"Connecting to Telegram (session: {self.config.session_file})")
                
                self._client = TelegramClient(
                    self.config.session_file,
                    self.config.api_id,
                    self.config.api_hash,
                    system_version=self.config.system_version,
                    device_model=self.config.device_model,
                    app_version=self.config.app_version,
                    flood_sleep_threshold=self.config.flood_sleep_threshold,
                )
                
                await self._client.connect()
                
                # Check if already authorized
                if not await self._client.is_user_authorized():
                    self.logger.warning(
                        "Session not authorized. Run setup script to authenticate: "
                        "python scripts/setup_telegram.py"
                    )
                    return False
                
                self._connected = True
                me = await self._client.get_me()
                self.logger.info(f"Connected as: {me.username or me.first_name} (ID: {me.id})")
                
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to connect: {e}")
                self._connected = False
                return False
    
    async def disconnect(self):
        """Disconnect from Telegram."""
        if self._client:
            await self._client.disconnect()
            self._connected = False
            self.logger.info("Disconnected from Telegram")
    
    async def send_message(
        self,
        chat_id: Union[str, int],
        text: str,
        parse_mode: str = "html",
        reply_to: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to a chat.
        
        Args:
            chat_id: Chat ID, username, or dialog identifier
            text: Message text
            parse_mode: Parse mode ('html', 'md', or None)
            reply_to: Message ID to reply to
            
        Returns:
            Result dict with success status
        """
        if not self.is_connected:
            connected = await self.connect()
            if not connected:
                return {"success": False, "error": "Not connected to Telegram"}
        
        try:
            # Resolve chat ID
            entity = await self._resolve_entity(chat_id)
            
            if entity is None:
                return {"success": False, "error": f"Could not resolve chat: {chat_id}"}
            
            # Send message
            message = await self._client.send_message(
                entity,
                text,
                parse_mode=parse_mode,
                reply_to=reply_to,
            )
            
            self.logger.info(f"Message sent to {chat_id} (msg_id: {message.id})")
            
            return {
                "success": True,
                "message_id": message.id,
                "chat_id": chat_id,
                "timestamp": datetime.now().isoformat(),
            }
            
        except FloodWaitError as e:
            self.logger.warning(f"Flood wait: {e.seconds} seconds")
            return {"success": False, "error": f"Rate limited. Wait {e.seconds}s", "retry_after": e.seconds}
        
        except ChatWriteForbiddenError:
            return {"success": False, "error": "Cannot write to this chat (no permission)"}
        
        except ChannelPrivateError:
            return {"success": False, "error": "Channel is private"}
        
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_report(
        self,
        report: str,
        query: str,
        chat_id: Optional[Union[str, int]] = None,
        run_id: Optional[int] = None,
        stats: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send a formatted OSINT report.
        
        Args:
            report: Report content
            query: Investigation query
            chat_id: Target chat (uses default if not specified)
            run_id: Optional run ID
            stats: Optional statistics
            
        Returns:
            Result dict
        """
        target = chat_id or self._target_dialog
        
        if not target:
            return {"success": False, "error": "No target chat specified"}
        
        # Format the report
        formatted = self.formatter.format_osint_report(
            report=report,
            query=query,
            run_id=run_id,
            stats=stats,
        )
        
        return await self.send_message(target, formatted, parse_mode="html")
    
    async def _resolve_entity(self, identifier: Union[str, int]) -> Any:
        """
        Resolve a chat identifier to a Telethon entity.
        
        Handles:
        - Numeric IDs
        - Usernames (@username)
        - Dialog format (cht[123456])
        """
        try:
            # Handle cht[id] format from MCP
            if isinstance(identifier, str) and identifier.startswith("cht["):
                match = re.match(r'cht\[(-?\d+)\]', identifier)
                if match:
                    identifier = int(match.group(1))
            
            # Handle @username format
            if isinstance(identifier, str) and identifier.startswith("@"):
                identifier = identifier[1:]  # Remove @
            
            # Try to get entity
            return await self._client.get_entity(identifier)
            
        except Exception as e:
            self.logger.error(f"Failed to resolve entity {identifier}: {e}")
            return None
    
    async def list_dialogs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List recent dialogs.
        
        Args:
            limit: Maximum number of dialogs
            
        Returns:
            List of dialog info dicts
        """
        if not self.is_connected:
            await self.connect()
        
        dialogs = []
        async for dialog in self._client.iter_dialogs(limit=limit):
            dialog_info = {
                "id": dialog.id,
                "name": dialog.name,
                "title": dialog.title,
                "unread_count": dialog.unread_count,
                "is_group": dialog.is_group,
                "is_channel": dialog.is_channel,
            }
            dialogs.append(dialog_info)
            
            # Cache for resolution
            self._dialogs_cache[dialog.name.lower()] = dialog.id
            self._dialogs_cache[str(dialog.id)] = dialog.id
        
        return dialogs
    
    async def get_messages(
        self,
        chat_id: Union[str, int],
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get recent messages from a chat.
        
        Args:
            chat_id: Chat identifier
            limit: Maximum messages to retrieve
            
        Returns:
            List of message dicts
        """
        if not self.is_connected:
            await self.connect()
        
        entity = await self._resolve_entity(chat_id)
        if not entity:
            return []
        
        messages = []
        async for message in self._client.iter_messages(entity, limit=limit):
            msg_info = {
                "id": message.id,
                "text": message.text or "",
                "date": message.date.isoformat() if message.date else None,
                "sender_id": message.sender_id,
                "reply_to": message.reply_to_msg_id,
            }
            messages.append(msg_info)
        
        return messages
    
    async def get_dialog_messages(
        self,
        dialog_id: Union[str, int],
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Alias for get_messages for backward compatibility.
        
        Args:
            dialog_id: Dialog/chat identifier
            limit: Maximum messages to retrieve
            
        Returns:
            List of message dicts
        """
        return await self.get_messages(dialog_id, limit)


# =============================================================================
# Report Publisher
# =============================================================================

class TelethonReportPublisher:
    """
    High-level publisher for OSINT reports using Telethon.
    
    Provides:
    - Formatted report publishing
    - Automatic message splitting for long reports
    - Error handling and retries
    - Local backup on failure
    """
    
    def __init__(self, target_dialog: Optional[str] = None):
        """
        Initialize the publisher.
        
        Args:
            target_dialog: Default dialog to publish to
        """
        # Use singleton client to avoid database locks
        self.client = get_telegram_client()
        self.target_dialog = target_dialog or os.getenv("TELEGRAM_TARGET_DIALOG", "")
        self.logger = logging.getLogger(self.__class__.__name__)
        self._connected = False
    
    async def ensure_connected(self) -> bool:
        """Ensure client is connected."""
        if not self._connected:
            self._connected = await self.client.connect()
        return self._connected
    
    async def publish_report(
        self,
        report_markdown: str,
        query: str,
        run_id: Optional[int] = None,
        stats: Optional[Dict[str, Any]] = None,
        dialog_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish an OSINT report to Telegram.
        
        Args:
            report_markdown: Report in markdown format
            query: Original query
            run_id: Optional run ID
            stats: Optional statistics
            dialog_name: Target dialog
            
        Returns:
            Publication result
        """
        target = dialog_name or self.target_dialog
        
        if not target:
            self.logger.warning("No target dialog specified")
            return await self._save_report_locally(
                "unknown", report_markdown, "No target dialog"
            )
        
        if not await self.ensure_connected():
            self.logger.error("Could not connect to Telegram")
            return await self._save_report_locally(
                target, report_markdown, "Connection failed"
            )
        
        result = await self.client.send_report(
            report=report_markdown,
            query=query,
            chat_id=target,
            run_id=run_id,
            stats=stats,
        )
        
        if result.get("success"):
            self.logger.info(f"Report published to Telegram: {target}")
        else:
            self.logger.error(f"Failed to publish report: {result.get('error')}")
            await self._save_report_locally(target, report_markdown, result.get('error', 'Unknown'))
        
        return result
    
    async def _save_report_locally(
        self,
        dialog: str,
        content: str,
        error: str
    ) -> Dict[str, Any]:
        """Save report locally as fallback."""
        import os
        from datetime import datetime
        
        reports_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "telegram_reports"
        )
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.md"
        filepath = os.path.join(reports_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(f"# OSINT Report\n\n")
            f.write(f"Target Dialog: {dialog}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Publish Error: {error}\n\n")
            f.write("---\n\n")
            f.write(content)
        
        self.logger.info(f"Report saved locally: {filepath}")
        
        return {
            "success": False,
            "saved_locally": True,
            "filepath": filepath,
            "error": error
        }
    
    async def close(self):
        """Close the connection."""
        if self.client:
            await self.client.disconnect()


# =============================================================================
# Factory function
# =============================================================================

def get_telegram_client() -> TelethonClient:
    """
    Get a configured Telegram client (singleton).
    
    Uses Telethon for direct integration.
    Always returns the same instance to avoid SQLite database locks.
    
    Returns:
        TelethonClient instance
    """
    global _telethon_client_instance
    
    if not TELETHON_AVAILABLE:
        raise ImportError("Telethon not installed. Run: pip install telethon")
    
    with _telethon_client_lock:
        if _telethon_client_instance is None:
            _telethon_client_instance = TelethonClient()
        return _telethon_client_instance


def get_telegram_publisher() -> TelethonReportPublisher:
    """
    Get a configured Telegram report publisher.
    
    Returns:
        TelethonReportPublisher instance
    """
    return TelethonReportPublisher()
