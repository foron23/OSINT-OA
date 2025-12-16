# =============================================================================
# Telegram MCP Client
# =============================================================================
"""
Client for connecting to the Telegram MCP Server.

Supports two modes of operation:
1. SERVICE MODE (recommended for Docker): Connect to HTTP service on port 5001
2. DIRECT MODE: Start telegram-mcp binary on-demand for each operation

Uses the juananpe/telegram-mcp fork with send-direct support.

Features:
- Send messages directly (not as drafts)
- List dialogs and messages
- Message caching and resolution
- Automatic fallback between modes
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class MCPConfig:
    """Configuration for the Telegram MCP server."""
    app_id: str
    api_hash: str
    session_path: str = ""
    # Service mode configuration
    service_url: str = ""
    use_service: bool = False
    
    @classmethod
    def from_env(cls) -> "MCPConfig":
        """Create config from environment variables."""
        # Check if service mode is enabled
        service_url = os.getenv("TELEGRAM_MCP_SERVICE_URL", "")
        use_service = os.getenv("TELEGRAM_MCP_USE_SERVICE", "auto").lower()
        
        # Auto-detect service mode
        if use_service == "auto":
            # If running in Docker or service URL is set, prefer service mode
            use_service_bool = bool(service_url) or os.path.exists("/.dockerenv")
        else:
            use_service_bool = use_service == "true"
        
        if not service_url and use_service_bool:
            service_url = "http://localhost:5001"
        
        return cls(
            app_id=os.getenv("TG_APP_ID", os.getenv("TELEGRAM_APP_ID", "")),
            api_hash=os.getenv("TG_API_HASH", os.getenv("TELEGRAM_API_HASH", "")),
            session_path=os.getenv("TELEGRAM_SESSION_PATH", ""),
            service_url=service_url,
            use_service=use_service_bool
        )
    
    @property
    def is_valid(self) -> bool:
        """Check if config has required fields."""
        return bool(self.app_id and self.api_hash)


# =============================================================================
# HTTP Client for Service Mode
# =============================================================================

class TelegramMCPServiceClient:
    """
    Cliente HTTP para conectarse al servicio Telegram MCP.
    
    Este cliente se usa cuando TELEGRAM_MCP_USE_SERVICE=true
    y conecta al servicio HTTP en puerto 5001.
    """
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url.rstrip("/")
        self.logger = logging.getLogger(self.__class__.__name__)
        self._session = None
    
    async def _get_session(self):
        """Obtener sesión HTTP (lazy initialization)."""
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Cerrar sesión HTTP."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def is_available(self) -> bool:
        """Verificar si el servicio está disponible."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/health", timeout=2) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("status") == "healthy"
        except Exception as e:
            self.logger.debug(f"Service not available: {e}")
        return False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Llamar a una herramienta MCP via el servicio HTTP.
        
        Args:
            tool_name: Nombre de la herramienta (tg_dialogs, tg_send, etc.)
            arguments: Argumentos de la herramienta
            
        Returns:
            Resultado de la herramienta
        """
        session = await self._get_session()
        
        try:
            async with session.post(
                f"{self.base_url}/tool/{tool_name}",
                json=arguments,
                timeout=30
            ) as resp:
                data = await resp.json()
                
                if resp.status == 200 and data.get("success"):
                    return data.get("result", {})
                else:
                    raise RuntimeError(data.get("error", f"HTTP {resp.status}"))
                    
        except Exception as e:
            self.logger.error(f"Service call failed: {e}")
            raise


# =============================================================================
# Main Client
# =============================================================================


class TelegramMCPClient:
    """
    Client for interacting with the Telegram MCP Server.
    
    Supports two modes:
    1. SERVICE MODE: Connect to HTTP service (recommended for Docker)
    2. DIRECT MODE: Start binary on-demand (for development)
    
    The MCP server provides these tools:
    - tg_dialogs: List telegram dialogs (chats, channels, users)
    - tg_dialog: Get messages from a dialog
    - tg_send: Send a message to a dialog
    - tg_read: Mark messages as read
    - tg_me: Get current account info
    """
    
    def __init__(self, config: Optional[MCPConfig] = None):
        """
        Initialize the Telegram MCP client.
        
        Args:
            config: MCP configuration, or load from environment
        """
        self.config = config or MCPConfig.from_env()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._dialogs_cache: Dict[str, str] = {}  # title -> name mapping
        self._target_dialog = os.getenv("TELEGRAM_TARGET_DIALOG", "")
        self._binary_path = self._get_binary_path()
        
        # Service client (lazy initialization)
        self._service_client: Optional[TelegramMCPServiceClient] = None
        self._service_available: Optional[bool] = None
    
    def _get_binary_path(self) -> str:
        """Get path to the telegram-mcp binary."""
        # Check environment variable first
        env_path = os.getenv("TELEGRAM_MCP_PATH", "")
        if env_path and os.path.exists(env_path):
            return env_path
        
        # Check multiple possible locations
        locations = [
            # Docker path
            "/app/bin/telegram-mcp",
            # Local bin directory
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "bin", "telegram-mcp"
            ),
            # Project root
            os.path.join(os.getcwd(), "bin", "telegram-mcp"),
        ]
        
        for path in locations:
            if os.path.exists(path):
                return path
        
        return ""
    
    @property
    def is_configured(self) -> bool:
        """Check if Telegram credentials are configured."""
        return self.config.is_valid
    
    @property
    def has_local_binary(self) -> bool:
        """Check if local telegram-mcp binary exists."""
        return bool(self._binary_path and os.path.exists(self._binary_path))
    
    @property
    def use_service_mode(self) -> bool:
        """Check if service mode is configured."""
        return self.config.use_service and bool(self.config.service_url)
    
    async def _get_service_client(self) -> Optional[TelegramMCPServiceClient]:
        """Get service client, checking availability."""
        if not self.use_service_mode:
            return None
        
        if self._service_client is None:
            self._service_client = TelegramMCPServiceClient(self.config.service_url)
        
        # Check availability (cached for performance, but reset on None)
        if self._service_available is None:
            self._service_available = await self._service_client.is_available()
            if self._service_available:
                self.logger.info(f"Using Telegram MCP service at {self.config.service_url}")
            else:
                self.logger.warning(f"Telegram MCP service not available, falling back to direct mode")
        
        return self._service_client if self._service_available else None
    
    def reset_service_cache(self):
        """Reset the service availability cache to force a fresh check."""
        self._service_available = None
    
    @property
    def has_local_binary(self) -> bool:
        """Check if local telegram-mcp binary exists."""
        return bool(self._binary_path and os.path.exists(self._binary_path))
    
    async def list_dialogs(self, only_unread: bool = False) -> List[Dict[str, Any]]:
        """
        List Telegram dialogs and cache name mappings.
        
        Args:
            only_unread: If True, only return unread dialogs
            
        Returns:
            List of dialog dictionaries
        """
        try:
            result = await self._call_mcp_tool("tg_dialogs", {
                "only_unread": only_unread
            })
            dialogs = result.get("dialogs", [])
            
            # Update cache: map title to name
            for d in dialogs:
                if d.get("name") and d.get("title"):
                    self._dialogs_cache[d["title"].lower()] = d["name"]
            
            return dialogs
        except Exception as e:
            self.logger.error(f"Failed to list dialogs: {e}")
            return []
    
    async def get_dialog_messages(
        self,
        dialog_name: str,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get messages from a dialog.
        
        Args:
            dialog_name: Name of the dialog
            offset: Message offset for pagination
            
        Returns:
            Dict with messages and metadata
        """
        try:
            result = await self._call_mcp_tool("tg_dialog", {
                "name": dialog_name,
                "offset": offset
            })
            return result
        except Exception as e:
            self.logger.error(f"Failed to get messages: {e}")
            return {"messages": [], "error": str(e)}
    
    async def resolve_dialog_name(self, title_or_name: str) -> str:
        """
        Resolve a dialog title to its MCP name.
        
        For group chats, the MCP name format is: cht[chat_id]
        For channels, it's the channel username.
        
        Args:
            title_or_name: Dialog title or name
            
        Returns:
            Resolved MCP dialog name
        """
        # If already in correct format, return as-is
        if title_or_name.startswith("cht[") or title_or_name.startswith("@"):
            return title_or_name
        
        # Check cache first
        cache_key = title_or_name.lower()
        if cache_key in self._dialogs_cache:
            return self._dialogs_cache[cache_key]
        
        # Fetch dialogs to populate cache
        await self.list_dialogs()
        
        # Check cache again
        if cache_key in self._dialogs_cache:
            return self._dialogs_cache[cache_key]
        
        # Return original if not found
        self.logger.warning(f"Could not resolve dialog name: {title_or_name}")
        return title_or_name
    
    async def send_message(
        self,
        dialog_name: str,
        text: str,
        send_direct: bool = True,
        resolve_name: bool = True
    ) -> Dict[str, Any]:
        """
        Send a message to a Telegram dialog.
        
        Args:
            dialog_name: Name or title of the dialog
            text: Message text (supports Markdown)
            send_direct: If True, send directly (not as draft)
            resolve_name: If True, attempt to resolve title to MCP name
            
        Returns:
            Result of the send operation
        """
        # Use default target if none specified
        if not dialog_name:
            dialog_name = self._target_dialog
        
        if not dialog_name:
            return self._error_result("No target dialog specified")
        
        if not self.is_configured:
            return self._error_result("Telegram MCP not configured")
        
        try:
            # Resolve dialog name if needed
            target_name = dialog_name
            if resolve_name and not dialog_name.startswith("cht["):
                target_name = await self.resolve_dialog_name(dialog_name)
                if target_name != dialog_name:
                    self.logger.debug(f"Resolved '{dialog_name}' -> '{target_name}'")
            
            # Send the message with send_direct option
            result = await self._call_mcp_tool("tg_send", {
                "name": target_name,
                "text": text,
                "send": send_direct  # True = send directly, False = save as draft
            })
            
            mode = "directly" if send_direct else "as draft"
            self.logger.info(f"Message sent {mode} to {target_name}")
            
            return {
                "success": True,
                "result": result,
                "dialog": target_name,
                "send_direct": send_direct,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return self._error_result(str(e), dialog_name)
    
    async def mark_as_read(self, dialog_name: str) -> Dict[str, Any]:
        """
        Mark messages in a dialog as read.
        
        Args:
            dialog_name: Name of the dialog
            
        Returns:
            Result of the operation
        """
        try:
            result = await self._call_mcp_tool("tg_read", {
                "name": dialog_name
            })
            return {"success": True, "result": result}
        except Exception as e:
            self.logger.error(f"Failed to mark as read: {e}")
            return self._error_result(str(e))
    
    async def get_me(self) -> Dict[str, Any]:
        """
        Get current Telegram account info.
        
        Returns:
            Account information
        """
        try:
            return await self._call_mcp_tool("tg_me", {})
        except Exception as e:
            self.logger.error(f"Failed to get account info: {e}")
            return {}
    
    def _error_result(
        self,
        error: str,
        dialog_name: str = None
    ) -> Dict[str, Any]:
        """Create an error result dict."""
        return {
            "success": False,
            "error": error,
            "dialog": dialog_name,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _call_mcp_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call an MCP tool via the Telegram MCP server.
        
        Supports two modes:
        1. SERVICE MODE: Call via HTTP service (faster, persistent connection)
        2. DIRECT MODE: Start binary on-demand (slower, for development)
        
        Uses the juananpe/telegram-mcp fork with send-direct support.
        
        Args:
            tool_name: Name of the MCP tool
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        # Try service mode first
        service_client = await self._get_service_client()
        if service_client:
            try:
                self.logger.debug(f"Calling MCP tool via service: {tool_name}")
                return await service_client.call_tool(tool_name, arguments)
            except Exception as e:
                self.logger.warning(f"Service call failed, falling back to direct mode: {e}")
                self._service_available = False
        
        # Fall back to direct mode (starting binary on-demand)
        return await self._call_mcp_tool_direct(tool_name, arguments)
    
    async def _call_mcp_tool_direct(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call an MCP tool directly by starting the binary.
        
        This is the original implementation - starts a new process for each call.
        """
        try:
            from mcp import ClientSession
            from mcp.client.stdio import stdio_client, StdioServerParameters
            
            # Get server parameters
            server_params = self._get_server_params()
            
            self.logger.debug(f"Calling MCP tool (direct): {tool_name}")
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    
                    # Parse the result
                    if result.content:
                        for content in result.content:
                            if hasattr(content, 'text'):
                                try:
                                    return json.loads(content.text)
                                except json.JSONDecodeError:
                                    return {"text": content.text}
                    
                    return {"success": True}
                    
        except Exception as e:
            self.logger.error(f"MCP tool call failed: {e}")
            raise
    
    def _get_server_params(self):
        """Get MCP server parameters based on binary availability."""
        from mcp.client.stdio import StdioServerParameters
        
        if self.has_local_binary:
            # Use local binary with send-direct support
            return StdioServerParameters(
                command=self._binary_path,
                args=[],
                env={
                    **os.environ,
                    "TG_APP_ID": self.config.app_id,
                    "TG_API_HASH": self.config.api_hash,
                }
            )
        else:
            # Fall back to npx (original chaindead version - drafts only)
            args = [
                "@chaindead/telegram-mcp",
                "--app-id", self.config.app_id,
                "--api-hash", self.config.api_hash
            ]
            
            if self.config.session_path:
                args.extend(["--session", self.config.session_path])
            
            return StdioServerParameters(
                command="npx",
                args=args,
                env={**os.environ, "NODE_NO_WARNINGS": "1"}
            )


class TelegramReportPublisher:
    """
    High-level publisher for sending OSINT reports to Telegram.
    
    Wraps TelegramMCPClient with report formatting and error handling.
    """
    
    def __init__(self, target_dialog: Optional[str] = None):
        """
        Initialize the publisher.
        
        Args:
            target_dialog: Default dialog to publish to
        """
        self.client = TelegramMCPClient()
        self.target_dialog = target_dialog or os.getenv("TELEGRAM_TARGET_DIALOG", "")
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def publish_report(
        self,
        report_markdown: str,
        query: str,
        stats: Optional[Dict[str, Any]] = None,
        dialog_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish an OSINT report to Telegram.
        
        Args:
            report_markdown: Report content in Markdown
            query: Original query
            stats: Optional statistics
            dialog_name: Target dialog (or use default)
            
        Returns:
            Publication result
        """
        target = dialog_name or self.target_dialog
        stats = stats or {}
        
        if not target:
            self.logger.warning("No target dialog specified")
            return await self._save_report_locally("unknown", report_markdown, "No target dialog")
        
        message = self._format_report_message(report_markdown, query, stats)
        result = await self.client.send_message(target, message)
        
        if result.get("success"):
            self.logger.info(f"Report published to Telegram: {target}")
        else:
            self.logger.error(f"Failed to publish report: {result.get('error')}")
            # Save locally as fallback
            await self._save_report_locally(target, report_markdown, result.get('error', 'Unknown error'))
        
        return result
    
    def _format_report_message(
        self,
        report: str,
        query: str,
        stats: Dict[str, Any]
    ) -> str:
        """Format the report for Telegram with rich formatting.
        
        Uses Telegram Markdown V2 compatible formatting with:
        - Clear visual hierarchy with emojis
        - Structured sections
        - Actionable insights highlighted
        - Compact but informative layout
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
        
        # Build header with query info
        header = f"""🔍 **INFORME DE INTELIGENCIA OSINT**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **Consulta:** `{query}`
🕐 **Fecha:** {timestamp}
"""
        
        # Build statistics section if available
        stats_section = ""
        if stats:
            total = stats.get('total_results', 0)
            sources = stats.get('sources_used', [])
            duration = stats.get('duration_seconds', 0)
            
            # Determine severity/importance indicator
            if total == 0:
                indicator = "⚪"
                status = "Sin resultados"
            elif total < 5:
                indicator = "🟢"
                status = "Baja exposición"
            elif total < 15:
                indicator = "🟡"
                status = "Exposición moderada"
            else:
                indicator = "🔴"
                status = "Alta exposición"
            
            stats_section = f"""
📊 **ESTADÍSTICAS**
├─ {indicator} Estado: {status}
├─ 📈 Resultados: {total}
├─ 🔌 Fuentes: {', '.join(sources) if sources else 'N/A'}
└─ ⏱️ Duración: {duration:.1f}s

"""
        
        # Process report content for better formatting
        formatted_report = self._enhance_report_formatting(report)
        
        # Build footer
        footer = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 _Generado por OSINT News Aggregator_
🔗 _Powered by LangChain + BBOT + Maigret_"""
        
        full_message = header + stats_section + formatted_report + footer
        
        # Telegram message limit (4096 chars) - leave room for potential escaping
        if len(full_message) > 3900:
            # Try to truncate intelligently at paragraph breaks
            truncated = self._smart_truncate(full_message, 3800)
            full_message = truncated + "\n\n⚠️ _[Informe truncado - Ver documento completo para detalles]_" + footer
        
        return full_message
    
    def _enhance_report_formatting(self, report: str) -> str:
        """Enhance report formatting with visual indicators.
        
        Adds emojis and structure to common OSINT report sections.
        """
        import re
        
        # Section headers mappings
        section_emojis = {
            r'(#+\s*)?(Subdominios?|Subdomains?)': '🌐 **SUBDOMINIOS**',
            r'(#+\s*)?(Perfiles?|Profiles?|Cuentas?|Accounts?)': '👤 **PERFILES ENCONTRADOS**',
            r'(#+\s*)?(Emails?|Correos?)': '📧 **DIRECCIONES DE EMAIL**',
            r'(#+\s*)?(Tecnolog[íi]as?|Technologies?|Tech Stack)': '⚙️ **TECNOLOGÍAS DETECTADAS**',
            r'(#+\s*)?(DNS|Registros? DNS)': '🔗 **REGISTROS DNS**',
            r'(#+\s*)?(Vulnerabilidades?|Vulnerabilities?)': '⚠️ **VULNERABILIDADES**',
            r'(#+\s*)?(Resumen|Summary|Conclusi[óo]n)': '📋 **RESUMEN**',
            r'(#+\s*)?(Recomendaciones?|Recommendations?)': '💡 **RECOMENDACIONES**',
            r'(#+\s*)?(Hallazgos?|Findings?)': '🔎 **HALLAZGOS**',
            r'(#+\s*)?(Redes Sociales|Social Media)': '📱 **REDES SOCIALES**',
            r'(#+\s*)?(Fuentes?|Sources?)': '📚 **FUENTES**',
        }
        
        enhanced = report
        for pattern, replacement in section_emojis.items():
            enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
        
        # Highlight URLs 
        enhanced = re.sub(
            r'(https?://[^\s\)]+)',
            r'`\1`',
            enhanced
        )
        
        # Format list items with better bullets
        enhanced = re.sub(r'^[-*]\s+', '• ', enhanced, flags=re.MULTILINE)
        enhanced = re.sub(r'^\d+\.\s+', '▸ ', enhanced, flags=re.MULTILINE)
        
        # Highlight important findings (wrapped in ** for bold)
        warning_patterns = [
            r'(exposed|expuesto)',
            r'(vulnerable|vulnerabilidad)',
            r'(crítico|critical)',
            r'(leaked|filtrado)',
            r'(sensitive|sensible)',
        ]
        for pattern in warning_patterns:
            enhanced = re.sub(
                pattern,
                r'⚠️ **\1**',
                enhanced,
                flags=re.IGNORECASE
            )
        
        return enhanced
    
    def _smart_truncate(self, text: str, max_length: int) -> str:
        """Truncate text intelligently at paragraph or sentence boundaries."""
        if len(text) <= max_length:
            return text
        
        # Try to find a good break point
        truncated = text[:max_length]
        
        # Try paragraph break first (double newline)
        last_para = truncated.rfind('\n\n')
        if last_para > max_length * 0.7:
            return truncated[:last_para]
        
        # Try single newline
        last_newline = truncated.rfind('\n')
        if last_newline > max_length * 0.8:
            return truncated[:last_newline]
        
        # Try sentence end
        for end_char in ['. ', '! ', '? ']:
            last_sentence = truncated.rfind(end_char)
            if last_sentence > max_length * 0.8:
                return truncated[:last_sentence + 1]
        
        # Fall back to hard truncate
        return truncated
    
    async def _save_report_locally(
        self,
        dialog_name: str,
        text: str,
        error: str
    ) -> Dict[str, Any]:
        """Save report to local file as fallback."""
        try:
            report_dir = "./data/telegram_reports"
            os.makedirs(report_dir, exist_ok=True)
            report_file = f"{report_dir}/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            
            with open(report_file, 'w') as f:
                f.write(f"# Report for: {dialog_name}\n")
                f.write(f"# Error: {error}\n\n")
                f.write(text)
            
            self.logger.info(f"Report saved locally: {report_file}")
            return {"success": True, "saved_to_file": report_file, "original_error": error}
        except Exception as save_error:
            return {"success": False, "error": error, "save_error": str(save_error)}
    
    async def send_alert(
        self,
        title: str,
        description: str,
        severity: str = "info",
        details: Optional[Dict[str, Any]] = None,
        dialog_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a security alert to Telegram.
        
        Args:
            title: Alert title
            description: Alert description
            severity: One of 'critical', 'high', 'medium', 'low', 'info'
            details: Additional details dict
            dialog_name: Target dialog (or use default)
            
        Returns:
            Send result
        """
        target = dialog_name or self.target_dialog
        if not target:
            self.logger.warning("No target dialog for alert")
            return {"success": False, "error": "No target dialog"}
        
        message = self._format_alert_message(title, description, severity, details)
        return await self.client.send_message(target, message)
    
    def _format_alert_message(
        self,
        title: str,
        description: str,
        severity: str,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format an alert message for Telegram."""
        severity_map = {
            'critical': ('🚨', 'CRÍTICO', '🔴'),
            'high': ('⚠️', 'ALTO', '🟠'),
            'medium': ('⚡', 'MEDIO', '🟡'),
            'low': ('ℹ️', 'BAJO', '🟢'),
            'info': ('📌', 'INFO', '🔵'),
        }
        
        emoji, label, indicator = severity_map.get(severity.lower(), ('📌', 'INFO', '🔵'))
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
        
        message = f"""{emoji} **ALERTA OSINT - {label}**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{indicator} **{title}**

{description}
"""
        
        if details:
            message += "\n📋 **Detalles:**\n"
            for key, value in details.items():
                if isinstance(value, list):
                    value = ', '.join(str(v) for v in value[:5])
                    if len(details[key]) > 5:
                        value += f"... (+{len(details[key]) - 5} más)"
                message += f"├─ {key}: `{value}`\n"
        
        message += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕐 {timestamp}
🤖 _OSINT News Aggregator_"""
        
        return message
    
    async def send_summary(
        self,
        title: str,
        findings: List[Dict[str, Any]],
        dialog_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a summary of multiple findings.
        
        Args:
            title: Summary title
            findings: List of finding dicts with 'type', 'count', 'items' keys
            dialog_name: Target dialog
            
        Returns:
            Send result
        """
        target = dialog_name or self.target_dialog
        if not target:
            return {"success": False, "error": "No target dialog"}
        
        message = self._format_summary_message(title, findings)
        return await self.client.send_message(target, message)
    
    def _format_summary_message(
        self,
        title: str,
        findings: List[Dict[str, Any]]
    ) -> str:
        """Format a summary message."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
        
        # Calculate totals
        total_items = sum(f.get('count', 0) for f in findings)
        
        type_emojis = {
            'subdomain': '🌐',
            'profile': '👤',
            'email': '📧',
            'technology': '⚙️',
            'vulnerability': '⚠️',
            'dns': '🔗',
            'social': '📱',
            'leak': '🔓',
            'default': '📌',
        }
        
        message = f"""📊 **RESUMEN OSINT**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **{title}**
📈 **Total de hallazgos:** {total_items}

"""
        
        for finding in findings:
            ftype = finding.get('type', 'default').lower()
            emoji = type_emojis.get(ftype, type_emojis['default'])
            count = finding.get('count', 0)
            items = finding.get('items', [])
            
            message += f"{emoji} **{ftype.title()}** ({count})\n"
            
            # Show first few items
            for item in items[:3]:
                if isinstance(item, dict):
                    item_text = item.get('name') or item.get('url') or str(item)
                else:
                    item_text = str(item)
                message += f"   • `{item_text[:50]}`\n"
            
            if len(items) > 3:
                message += f"   _... y {len(items) - 3} más_\n"
            message += "\n"
        
        message += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕐 {timestamp}
🤖 _OSINT News Aggregator_"""
        
        return message


# Convenience functions
def get_telegram_client() -> TelegramMCPClient:
    """Get a TelegramMCPClient instance."""
    return TelegramMCPClient()


def get_telegram_publisher(target_dialog: Optional[str] = None) -> TelegramReportPublisher:
    """Get a TelegramReportPublisher instance."""
    return TelegramReportPublisher(target_dialog)
