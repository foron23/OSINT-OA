# =============================================================================
# Telegram Message Listener
# =============================================================================
"""
Telegram Message Listener for OSINT Investigation Requests.

This service polls a Telegram chat for new messages and triggers
OSINT investigations based on commands.

Commands:
    /osint <query>    - Start an OSINT investigation
    /search <query>   - Search for specific information
    /status           - Get bot status
    /help             - Show help message

Natural Language:
    The bot also recognizes natural language requests containing:
    - "investiga", "busca", "analiza"
    - "investigate", "search for", "find info"
    - OSINT-related keywords
"""

import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Set, Callable

from integrations.telegram.telethon_client import TelethonClient, get_telegram_client

logger = logging.getLogger(__name__)


class MessageHandler:
    """Represents a message handler with pattern and callback."""
    
    def __init__(
        self,
        pattern: str,
        handler: Callable,
        is_regex: bool = False,
        description: str = ""
    ):
        self.pattern = pattern
        self.handler = handler
        self.is_regex = is_regex
        self.description = description
        self._compiled = re.compile(pattern, re.IGNORECASE) if is_regex else None
    
    def matches(self, text: str) -> bool:
        """Check if message matches this handler's pattern."""
        if self.is_regex:
            return bool(self._compiled.match(text))
        return text.lower().startswith(self.pattern.lower())
    
    def extract_args(self, text: str) -> str:
        """Extract arguments from the message."""
        if self.is_regex:
            match = self._compiled.match(text)
            if match and match.groups():
                return match.group(1).strip()
            return text
        
        if text.lower().startswith(self.pattern.lower()):
            return text[len(self.pattern):].strip()
        return text


class TelegramListener:
    """
    Polls Telegram for new messages and triggers investigations.
    
    Features:
    - Command-based investigation triggers
    - Natural language detection
    - Extensible handler system
    - Configurable polling interval
    """
    
    def __init__(
        self,
        target_dialog: Optional[str] = None,
        poll_interval: int = 10
    ):
        """
        Initialize the listener.
        
        Args:
            target_dialog: Dialog ID to listen to (e.g., cht[123456])
            poll_interval: Seconds between polls
        """
        self.target_dialog = target_dialog or os.getenv("TELEGRAM_TARGET_DIALOG", "")
        self.poll_interval = poll_interval
        self.processed_messages: Set[str] = set()
        self.running = False
        self.client = get_telegram_client()  # Uses Telethon
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Investigation callback
        self._investigation_callback: Optional[Callable] = None
        
        # OSINT keywords for natural language detection
        self.osint_keywords = [
            'investiga', 'busca información', 'buscar', 'analiza',
            'investigate', 'search for', 'find info', 'analyze',
            'osint', 'threat intel', 'ciberamenaza', 'ransomware',
            'vulnerabilidad', 'cve', 'malware', 'apt', 'phishing'
        ]
        
        # Initialize handlers
        self._handlers: List[MessageHandler] = []
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Set up default message handlers."""
        self.add_handler(MessageHandler(
            pattern=r"^/osint\s+(.+)",
            handler=self._handle_osint_command,
            is_regex=True,
            description="Start OSINT investigation"
        ))
        
        self.add_handler(MessageHandler(
            pattern=r"^/search\s+(.+)",
            handler=self._handle_search_command,
            is_regex=True,
            description="Quick search"
        ))
        
        self.add_handler(MessageHandler(
            pattern=r"^/run\s+(\d+)",
            handler=self._handle_run_detail_command,
            is_regex=True,
            description="View run details"
        ))
        
        self.add_handler(MessageHandler(
            pattern=r"^/traces\s+(\d+)",
            handler=self._handle_traces_command,
            is_regex=True,
            description="View run traces"
        ))
        
        self.add_handler(MessageHandler(
            pattern="/runs",
            handler=self._handle_list_runs_command,
            description="List recent runs"
        ))
        
        self.add_handler(MessageHandler(
            pattern="/status",
            handler=self._handle_status_command,
            description="Bot status"
        ))
        
        self.add_handler(MessageHandler(
            pattern="/help",
            handler=self._handle_help_command,
            description="Show help"
        ))
    
    def add_handler(self, handler: MessageHandler):
        """Add a message handler."""
        self._handlers.append(handler)
    
    def set_investigation_callback(self, callback: Callable):
        """
        Set the callback for running investigations.
        
        Args:
            callback: Async function(query: str, requester: str) -> Dict
        """
        self._investigation_callback = callback
    
    async def start(self):
        """Start listening for messages."""
        if not self.target_dialog:
            self.logger.error("No target dialog configured. Set TELEGRAM_TARGET_DIALOG.")
            return
        
        self.running = True
        self._log_startup_banner()
        
        # Wait for Telethon client to be available
        await self._wait_for_telegram_service()
        
        # Load initial messages to avoid re-processing old ones
        await self._initialize_processed_messages()
        
        # Start polling loop
        while self.running:
            try:
                await self._poll_for_messages()
            except Exception as e:
                self.logger.error(f"Poll error: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    async def _wait_for_telegram_service(self, max_retries: int = 30, retry_interval: int = 2):
        """Wait for the Telegram service to become available."""
        self.logger.info("Waiting for Telegram service to be available...")
        
        for attempt in range(max_retries):
            try:
                # Try to connect and verify service is ready
                if self.client:
                    # Test connection by trying to get dialogs
                    dialogs = await self.client.list_dialogs(limit=1)
                    if dialogs is not None:
                        self.logger.info("✅ Telegram service is available")
                        return
            except Exception as e:
                self.logger.debug(f"Service check failed: {e}")
            
            if attempt < max_retries - 1:
                self.logger.info(f"Waiting for Telegram service... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(retry_interval)
        
        self.logger.warning("⚠️ Telegram service not available after waiting, will retry on each poll")
    
    def stop(self):
        """Stop listening."""
        self.running = False
        self.logger.info("Listener stopped.")
    
    def _log_startup_banner(self):
        """Log startup information."""
        self.logger.info("=" * 60)
        self.logger.info("  OSINT Telegram Listener Starting")
        self.logger.info("=" * 60)
        self.logger.info(f"Target Dialog: {self.target_dialog}")
        self.logger.info(f"Poll Interval: {self.poll_interval}s")
        self.logger.info("=" * 60)
        self.logger.info("")
        self.logger.info("🤖 Listener active. Press Ctrl+C to stop.")
        self.logger.info("")
        self.logger.info("Supported commands:")
        for handler in self._handlers:
            if handler.description:
                pattern = handler.pattern if not handler.is_regex else handler.pattern.split("\\s")[0][1:]
                self.logger.info(f"  {pattern:12s} - {handler.description}")
        self.logger.info("")
    
    async def _initialize_processed_messages(self):
        """Load existing messages to avoid processing old ones."""
        try:
            messages = await self.client.get_dialog_messages(self.target_dialog)
            
            # Handle both list and dict formats
            if isinstance(messages, dict):
                messages = messages.get("messages", [])
            elif not isinstance(messages, list):
                messages = []
            
            for msg in messages:
                msg_key = self._get_message_key(msg)
                self.processed_messages.add(msg_key)
            
            self.logger.info(f"Initialized with {len(self.processed_messages)} existing messages")
            
        except Exception as e:
            self.logger.warning(f"Could not initialize messages: {e}")
    
    async def _poll_for_messages(self):
        """Poll for new messages and process them."""
        try:
            # get_dialog_messages returns List[Dict], not Dict with "messages" key
            messages = await self.client.get_dialog_messages(self.target_dialog)
            
            # Handle both list and dict formats for robustness
            if isinstance(messages, dict):
                messages = messages.get("messages", [])
            elif not isinstance(messages, list):
                messages = []
            
            # Process new messages (in reverse order - oldest first)
            for msg in reversed(messages):
                msg_key = self._get_message_key(msg)
                
                if msg_key not in self.processed_messages:
                    self.processed_messages.add(msg_key)
                    await self._process_message(msg)
                    
        except Exception as e:
            self.logger.error(f"Error polling messages: {e}")
    
    def _get_message_key(self, msg: Dict[str, Any]) -> str:
        """Generate a unique key for a message."""
        return f"{msg.get('when', '')}:{msg.get('text', '')[:50]}"
    
    async def _process_message(self, msg: Dict[str, Any]):
        """Process a new message."""
        text = msg.get("text", "")
        when = msg.get("when", "unknown")
        who = msg.get("who", "unknown")
        
        self.logger.info(f"New message [{when}] from {who}: {text[:80]}...")
        
        # Skip bot's own messages
        if self._is_own_message(text):
            self.logger.debug("Skipping own message")
            return
        
        # Try registered handlers first
        for handler in self._handlers:
            if handler.matches(text):
                args = handler.extract_args(text)
                await handler.handler(args, who)
                return
        
        # Check for natural language OSINT requests
        if self._is_osint_request(text):
            query = self._extract_query(text)
            if query:
                await self._start_investigation(query, who)
    
    def _is_own_message(self, text: str) -> bool:
        """Check if message is from this bot."""
        # Check for bot response patterns
        bot_prefixes = [
            "🔍 **",           # OSINT Bot responses
            "📊 **",           # Status responses  
            "📋 **",           # List responses
            "✅ **",           # Success messages
            "❌ **",           # Error messages
            "⚠️ **",           # Warning messages
            "🔬 **",           # Trace responses
            "##",              # Report headers
        ]
        
        for prefix in bot_prefixes:
            if text.startswith(prefix):
                return True
        
        return False
    
    def _is_osint_request(self, message: str) -> bool:
        """Check if message is an OSINT investigation request."""
        message_lower = message.lower()
        return any(kw in message_lower for kw in self.osint_keywords)
    
    def _extract_query(self, message: str) -> str:
        """Extract the query from a natural language request."""
        prefixes = [
            'investiga sobre', 'busca información sobre', 'analiza',
            'investigate', 'search for', 'find info about', 'analyze'
        ]
        
        message_clean = message
        for prefix in prefixes:
            if message.lower().startswith(prefix):
                message_clean = message[len(prefix):].strip()
                break
        
        return message_clean
    
    # =========================================================================
    # Command Handlers
    # =========================================================================
    
    async def _handle_osint_command(self, query: str, requester: str):
        """Handle /osint command."""
        if query:
            await self._start_investigation(query, requester)
    
    async def _handle_search_command(self, query: str, requester: str):
        """Handle /search command."""
        if query:
            await self._start_investigation(query, requester, quick=True)
    
    async def _handle_status_command(self, args: str, requester: str):
        """Handle /status command."""
        try:
            from agents.registry import AgentRegistry
            agents = AgentRegistry.list_available()
            available_count = len([a for a in agents if a.get('available')])
            total_count = len(agents)
        except Exception:
            available_count = "N/A"
            total_count = "N/A"
        
        await self.client.send_message(
            self.target_dialog,
            f"📊 **Estado del Bot OSINT**\n\n"
            f"✅ Conectado y escuchando\n"
            f"🤖 Agentes: {available_count}/{total_count} disponibles\n"
            f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"_Envía /help para ver comandos._"
        )
    
    async def _handle_help_command(self, args: str, requester: str):
        """Handle /help command."""
        await self.client.send_message(
            self.target_dialog,
            "🔍 **OSINT Bot - Ayuda**\n\n"
            "**Comandos de Investigación:**\n"
            "• `/osint <query>` - Iniciar investigación\n"
            "• `/search <query>` - Búsqueda rápida\n\n"
            "**Consulta de Resultados:**\n"
            "• `/runs` - Listar investigaciones recientes\n"
            "• `/run <id>` - Ver detalles de una investigación\n"
            "• `/traces <id>` - Ver trazas de ejecución\n\n"
            "**Sistema:**\n"
            "• `/status` - Ver estado del bot\n"
            "• `/help` - Ver esta ayuda\n\n"
            "**Ejemplos:**\n"
            "• `/osint ransomware attacks 2025`\n"
            "• `/run 42` - Ver investigación #42\n"
            "• `/traces 42` - Ver pasos de investigación #42\n"
            "• `Investiga sobre APT29`\n\n"
            "_También puedes escribir solicitudes en lenguaje natural._"
        )
    
    async def _handle_list_runs_command(self, args: str, requester: str):
        """Handle /runs command - list recent investigations."""
        try:
            from db import RunRepository
            
            runs = RunRepository.list_runs(limit=10)
            
            if not runs:
                await self.client.send_message(
                    self.target_dialog,
                    "📋 **Investigaciones Recientes**\n\n"
                    "_No hay investigaciones registradas._\n\n"
                    "_Usa `/osint <tema>` para iniciar una._"
                )
                return
            
            lines = ["📋 **Investigaciones Recientes**\n"]
            for run in runs:
                status_emoji = {
                    'completed': '✅',
                    'failed': '❌',
                    'started': '⏳',
                    'partial': '⚠️'
                }.get(run.status, '❓')
                
                query_short = run.query[:30] + "..." if len(run.query) > 30 else run.query
                lines.append(
                    f"{status_emoji} **#{run.id}** - {query_short}\n"
                    f"   _{run.started_at[:16] if run.started_at else 'N/A'}_"
                )
            
            lines.append("\n_Usa `/run <id>` para ver detalles._")
            
            await self.client.send_message(
                self.target_dialog,
                "\n".join(lines)
            )
            
        except Exception as e:
            self.logger.error(f"Error listing runs: {e}")
            await self.client.send_message(
                self.target_dialog,
                f"❌ Error al listar investigaciones: {str(e)}"
            )
    
    async def _handle_run_detail_command(self, run_id_str: str, requester: str):
        """Handle /run <id> command - show investigation details."""
        try:
            from db import RunRepository, ItemRepository, ReportRepository, TraceRepository
            
            run_id = int(run_id_str)
            run = RunRepository.get_by_id(run_id)
            
            if not run:
                await self.client.send_message(
                    self.target_dialog,
                    f"❌ Investigación #{run_id} no encontrada."
                )
                return
            
            item_count = ItemRepository.count_by_run(run_id)
            trace_count = TraceRepository.count_by_run(run_id)
            report = ReportRepository.get_by_run_id(run_id)
            
            status_emoji = {
                'completed': '✅',
                'failed': '❌',
                'started': '⏳',
                'partial': '⚠️'
            }.get(run.status, '❓')
            
            message = (
                f"📊 **Investigación #{run.id}**\n\n"
                f"**Query:** {run.query}\n"
                f"**Estado:** {status_emoji} {run.status}\n"
                f"**Iniciada:** {run.started_at[:16] if run.started_at else 'N/A'}\n"
                f"**Finalizada:** {run.finished_at[:16] if run.finished_at else 'En progreso'}\n"
                f"**Scope:** {run.scope or 'Sin restricciones'}\n\n"
                f"📈 **Métricas:**\n"
                f"• Items encontrados: {item_count}\n"
                f"• Trazas de ejecución: {trace_count}\n"
                f"• Reporte: {'✅ Generado' if report else '❌ No disponible'}\n"
            )
            
            if report and report.summary:
                summary_short = report.summary[:300]
                if len(report.summary) > 300:
                    summary_short += "..."
                message += f"\n**📝 Resumen:**\n_{summary_short}_\n"
            
            message += f"\n_Usa `/traces {run_id}` para ver los pasos de ejecución._"
            
            await self.client.send_message(self.target_dialog, message)
            
        except ValueError:
            await self.client.send_message(
                self.target_dialog,
                "❌ ID de investigación inválido. Usa: `/run <número>`"
            )
        except Exception as e:
            self.logger.error(f"Error getting run detail: {e}")
            await self.client.send_message(
                self.target_dialog,
                f"❌ Error al obtener detalles: {str(e)}"
            )
    
    async def _handle_traces_command(self, run_id_str: str, requester: str):
        """Handle /traces <id> command - show execution traces."""
        try:
            from db import RunRepository, TraceRepository
            
            run_id = int(run_id_str)
            run = RunRepository.get_by_id(run_id)
            
            if not run:
                await self.client.send_message(
                    self.target_dialog,
                    f"❌ Investigación #{run_id} no encontrada."
                )
                return
            
            # Get traces summary
            summary = TraceRepository.get_evidence_summary(run_id)
            traces = TraceRepository.get_by_run_id(run_id, include_full_data=False)
            
            if not traces:
                await self.client.send_message(
                    self.target_dialog,
                    f"🔬 **Trazas de Investigación #{run_id}**\n\n"
                    f"_No hay trazas registradas para esta investigación._"
                )
                return
            
            # Build summary message
            total_duration = summary.get('total_duration_ms', 0)
            duration_str = f"{total_duration / 1000:.2f}s" if total_duration else 'N/A'
            avg_conf = summary.get('avg_confidence')
            conf_str = f"{avg_conf * 100:.0f}%" if avg_conf else 'N/A'
            
            message = (
                f"🔬 **Trazas de Investigación #{run_id}**\n\n"
                f"**📊 Resumen:**\n"
                f"• Total trazas: {summary.get('total_traces', 0)}\n"
                f"• Evidencias encontradas: {summary.get('total_evidence', 0)}\n"
                f"• Completadas: {summary.get('completed_traces', 0)}\n"
                f"• Fallidas: {summary.get('failed_traces', 0)}\n"
                f"• Duración total: {duration_str}\n"
                f"• Confianza media: {conf_str}\n\n"
                f"**📋 Timeline:**\n"
            )
            
            # Add trace timeline (max 10 traces to avoid message length issues)
            type_icons = {
                'tool_call': '🔧',
                'agent_action': '🤖',
                'llm_reasoning': '💭',
                'decision': '🎯',
                'error': '❌',
                'checkpoint': '📍'
            }
            
            status_icons = {
                'completed': '✅',
                'failed': '❌',
                'running': '⏳',
                'pending': '⏸️',
                'skipped': '⏭️'
            }
            
            for i, trace in enumerate(traces[:10]):
                type_icon = type_icons.get(trace.trace_type, '📝')
                status_icon = status_icons.get(trace.status, '❓')
                
                tool_or_agent = trace.tool_name or trace.agent_name or 'Unknown'
                tool_short = tool_or_agent[:20] + "..." if len(tool_or_agent) > 20 else tool_or_agent
                
                evidence_str = f"📋{trace.evidence_count}" if trace.evidence_count > 0 else ""
                duration_str = f"⏱️{trace.duration_ms/1000:.1f}s" if trace.duration_ms else ""
                
                message += (
                    f"\n{i+1}. {type_icon} {status_icon} **{tool_short}**\n"
                    f"   {evidence_str} {duration_str}"
                )
                
                if trace.instruction:
                    instr_short = trace.instruction[:40] + "..." if len(trace.instruction) > 40 else trace.instruction
                    message += f"\n   _{instr_short}_"
            
            if len(traces) > 10:
                message += f"\n\n_...y {len(traces) - 10} trazas más. Consulta el panel web para ver todas._"
            
            await self.client.send_message(self.target_dialog, message)
            
        except ValueError:
            await self.client.send_message(
                self.target_dialog,
                "❌ ID de investigación inválido. Usa: `/traces <número>`"
            )
        except Exception as e:
            self.logger.error(f"Error getting traces: {e}")
            await self.client.send_message(
                self.target_dialog,
                f"❌ Error al obtener trazas: {str(e)}"
            )
    
    async def _start_investigation(
        self,
        query: str,
        requester: str,
        quick: bool = False
    ):
        """
        Start an OSINT investigation using the same flow as the web API.
        
        Creates a run_id, executes the investigation, saves the report,
        and publishes results to Telegram.
        """
        self.logger.info(f"Starting investigation: {query} (requested by {requester})")
        
        # Import repositories
        from db import RunRepository, ReportRepository, Report
        
        # Determine depth based on quick flag
        depth = "quick" if quick else "standard"
        limit = 10 if quick else 20
        
        # Create run record in database first (same as API)
        run_id = RunRepository.create(
            query=query,
            initiated_by=f"telegram:{requester}",
            limit_requested=limit,
            scope=None
        )
        
        self.logger.info(f"Created run #{run_id} for query: {query}")
        
        # Send acknowledgment with run_id
        mode = "Búsqueda rápida" if quick else "investigación OSINT"
        await self.client.send_message(
            self.target_dialog,
            f"🔍 **Iniciando {mode}**\n\n"
            f"🆔 Run ID: `{run_id}`\n"
            f"📝 Query: `{query}`\n"
            f"👤 Solicitado por: {requester}\n"
            f"⚙️ Profundidad: {depth}\n"
            f"⏳ Estado: En progreso...\n\n"
            f"_Usa `/run {run_id}` para ver el estado._"
        )
        
        try:
            # Run the investigation
            result = await self._run_default_investigation(
                query=query,
                requester=requester,
                run_id=run_id,
                depth=depth
            )
            
            if result.get('status') == 'completed':
                # Send success message with run reference
                report_preview = result.get('report_preview', '')
                await self.client.send_message(
                    self.target_dialog,
                    f"✅ **Investigación #{run_id} completada**\n\n"
                    f"📝 Query: `{query}`\n"
                    f"📊 Estado: Completada\n\n"
                    f"📋 **Resumen:**\n{report_preview}\n\n"
                    f"_Usa `/run {run_id}` para ver detalles completos._\n"
                    f"_Usa `/traces {run_id}` para ver trazas de ejecución._"
                )
            else:
                error_msg = result.get('error', 'Unknown error')
                await self.client.send_message(
                    self.target_dialog,
                    f"⚠️ **Investigación #{run_id} parcial**\n\n"
                    f"📊 Estado: {result.get('status', 'unknown')}\n"
                    f"❌ Error: {error_msg}\n\n"
                    f"_Usa `/run {run_id}` para más detalles._"
                )
                
        except Exception as e:
            self.logger.error(f"Investigation failed: {e}")
            # Update run status to failed
            RunRepository.update_status(run_id, "failed", stats={"error": str(e)})
            
            await self.client.send_message(
                self.target_dialog,
                f"❌ **Error en investigación #{run_id}**\n\n"
                f"Error: {str(e)}\n\n"
                f"_Intenta de nuevo más tarde._"
            )
    
    async def _run_default_investigation(
        self,
        query: str,
        requester: str,
        run_id: int,
        depth: str = "standard"
    ) -> Dict[str, Any]:
        """
        Run investigation using the same flow as /api/collect.
        
        This ensures investigations from Telegram have the same format
        and are stored with the same structure as web investigations.
        """
        from agents.control import ControlAgent
        from db import RunRepository, ReportRepository, Report
        
        try:
            # Initialize control agent
            control_agent = ControlAgent()
            
            # Run investigation (blocking operation, run in thread)
            # Pass run_id for tracing
            self.logger.info(f"Running investigation #{run_id} with depth={depth}")
            result = await asyncio.to_thread(
                control_agent.investigate,
                topic=query,
                depth=depth,
                run_id=run_id
            )
            
            # Extract report text
            report_text = result.get("report", "")
            
            # Store the report in database
            report_obj = Report(
                run_id=run_id,
                query=query,
                report=report_text,
                summary=f"Investigation: {query[:100]}"
            )
            report_id = ReportRepository.create(report_obj)
            self.logger.info(f"Stored report #{report_id} for run #{run_id}")
            
            # Publish full report to Telegram
            if report_text:
                await self._publish_report_to_telegram(
                    report_text=report_text,
                    query=query,
                    run_id=run_id
                )
            
            # Update run status to completed
            stats = {
                "depth": depth,
                "agents_used": result.get("metadata", {}).get("agents_used", "auto"),
                "initiated_by": f"telegram:{requester}",
                "telegram_published": True,
            }
            RunRepository.update_status(run_id, "completed", stats=stats)
            
            # Create preview for confirmation message
            report_preview = report_text[:500] + "..." if len(report_text) > 500 else report_text
            
            return {
                "status": "completed",
                "run_id": run_id,
                "report_id": report_id,
                "report_preview": report_preview,
                "result": result
            }
            
        except Exception as e:
            self.logger.error(f"Investigation #{run_id} failed: {e}")
            # Mark run as failed
            RunRepository.update_status(run_id, "failed", stats={"error": str(e)})
            return {"status": "error", "run_id": run_id, "error": str(e)}
    
    async def _publish_report_to_telegram(
        self,
        report_text: str,
        query: str,
        run_id: int
    ):
        """
        Publish the full investigation report to Telegram.
        
        Formats the report with header and handles length limits.
        """
        from datetime import datetime
        
        # Build header
        header = (
            f"🔍 **OSINT Intelligence Report**\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC\n"
            f"🎯 Query: `{query}`\n"
            f"🆔 Run ID: {run_id}\n\n"
            f"---\n\n"
        )
        
        # Telegram message limit is 4096 characters
        max_content = 4000 - len(header)
        
        if len(report_text) > max_content:
            report_text = report_text[:max_content - 100]
            report_text += f"\n\n... [Reporte truncado]\n_Ver completo con `/run {run_id}` o en la web._"
        
        message = header + report_text + "\n\n---\n_Generated by OSINT OA_"
        
        try:
            await self.client.send_message(self.target_dialog, message)
            self.logger.info(f"Published report for run #{run_id} to Telegram")
        except Exception as e:
            self.logger.error(f"Failed to publish report to Telegram: {e}")


async def run_listener():
    """Run the Telegram listener service."""
    # Configure logging for the listener
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    target_dialog = os.getenv("TELEGRAM_TARGET_DIALOG", "")
    poll_interval = int(os.getenv("TELEGRAM_POLL_INTERVAL", "10"))
    
    if not target_dialog:
        logger.error("❌ TELEGRAM_TARGET_DIALOG must be set in .env")
        return
    
    logger.info(f"🚀 Starting Telegram Listener for dialog: {target_dialog}")
    
    listener = TelegramListener(
        target_dialog=target_dialog,
        poll_interval=poll_interval
    )
    
    try:
        await listener.start()
    except KeyboardInterrupt:
        logger.info("\n👋 Listener stopped by user")
        listener.stop()
    except Exception as e:
        logger.error(f"❌ Listener error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_listener())
