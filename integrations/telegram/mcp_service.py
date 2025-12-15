#!/usr/bin/env python3
# =============================================================================
# Telegram MCP Service - HTTP Wrapper
# =============================================================================
"""
Servicio HTTP que wrappea el binario telegram-mcp para ejecutarse en paralelo
al servidor Flask principal.

Este servicio:
1. Mantiene una conexión persistente con el binario telegram-mcp
2. Expone endpoints HTTP para las operaciones de Telegram
3. Permite al cliente Flask comunicarse sin iniciar el binario cada vez

Arquitectura:
    ┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
    │  Flask API      │──────►│  Telegram MCP    │──────►│  telegram-mcp   │
    │  (puerto 5000)  │ HTTP  │  Service         │ stdio │  (binario Go)   │
    │                 │       │  (puerto 5001)   │       │                 │
    └─────────────────┘       └──────────────────┘       └─────────────────┘

Uso:
    python -m integrations.telegram.mcp_service
    
    O con el script:
    ./scripts/run_telegram_service.sh
"""

import asyncio
import json
import logging
import os
import signal
import sys
from typing import Any, Dict, Optional
from datetime import datetime
from contextlib import asynccontextmanager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TelegramMCPService")

# Añadir path del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TelegramMCPService:
    """
    Servicio que mantiene una conexión persistente con telegram-mcp.
    
    Beneficios sobre el modo on-demand:
    - Conexión persistente = menor latencia
    - Sesión mantenida activa
    - Un solo proceso de binario
    """
    
    def __init__(self):
        self.app_id = os.getenv("TG_APP_ID", os.getenv("TELEGRAM_APP_ID", ""))
        self.api_hash = os.getenv("TG_API_HASH", os.getenv("TELEGRAM_API_HASH", ""))
        self.session_path = os.getenv("TELEGRAM_SESSION_PATH", "")
        self.binary_path = self._find_binary()
        
        self._process: Optional[asyncio.subprocess.Process] = None
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._connected = False
        self._reader_task: Optional[asyncio.Task] = None
        self._stderr_task: Optional[asyncio.Task] = None
    
    def _find_binary(self) -> str:
        """Encontrar el binario telegram-mcp."""
        locations = [
            os.getenv("TELEGRAM_MCP_PATH", ""),
            "/app/bin/telegram-mcp",
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "bin", "telegram-mcp"),
            "./bin/telegram-mcp"
        ]
        
        for path in locations:
            if path and os.path.exists(path) and os.access(path, os.X_OK):
                logger.info(f"Found telegram-mcp binary: {path}")
                return path
        
        logger.error("telegram-mcp binary not found!")
        return ""
    
    def _get_session_file(self) -> str:
        """Encontrar el archivo de sesión de Telegram."""
        # Prioridad de búsqueda:
        # 1. Variable TG_SESSION_PATH (ruta completa al archivo)
        # 2. TELEGRAM_SESSION_PATH + session.json
        # 3. Rutas por defecto
        
        # Opción 1: Variable de entorno directa
        session_path = os.getenv("TG_SESSION_PATH", "")
        if session_path and os.path.isfile(session_path):
            return session_path
        
        # Opción 2: Directorio de sesión + session.json
        session_dir = self.session_path
        if session_dir:
            session_file = os.path.join(session_dir, "session.json")
            if os.path.isfile(session_file):
                return session_file
        
        # Opción 3: Rutas por defecto
        default_paths = [
            "/app/data/telegram-session/session.json",  # Docker
            os.path.expanduser("~/.telegram-mcp/session.json"),  # Host
            "./data/telegram-session/session.json",  # Local
        ]
        
        for path in default_paths:
            if os.path.isfile(path):
                return path
        
        # Si no existe, devolver la ruta esperada (para crear)
        if session_dir:
            return os.path.join(session_dir, "session.json")
        return "/app/data/telegram-session/session.json"
    
    @property
    def is_configured(self) -> bool:
        """Verificar si está configurado correctamente."""
        return bool(self.app_id and self.api_hash and self.binary_path)
    
    @property
    def is_connected(self) -> bool:
        """Verificar si está conectado al binario."""
        return self._connected and self._process is not None
    
    async def start(self) -> bool:
        """Iniciar el proceso telegram-mcp."""
        if not self.is_configured:
            logger.error("Telegram MCP not configured. Check TG_APP_ID and TG_API_HASH")
            return False
        
        try:
            logger.info("Starting telegram-mcp process...")
            
            # Determinar la ruta del archivo de sesión
            session_file = self._get_session_file()
            logger.info(f"Using session file: {session_file}")
            
            env = {
                **os.environ,
                "TG_APP_ID": self.app_id,
                "TG_API_HASH": self.api_hash,
            }
            
            # Añadir TG_SESSION_PATH si hay un archivo de sesión
            if session_file and os.path.exists(session_file):
                env["TG_SESSION_PATH"] = session_file
                logger.info(f"Session file exists: {session_file}")
            else:
                logger.warning(f"Session file not found: {session_file}")
            
            self._process = await asyncio.create_subprocess_exec(
                self.binary_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            self._connected = True
            
            # Iniciar tarea de lectura de respuestas
            self._reader_task = asyncio.create_task(self._read_responses())
            
            # Iniciar tarea de lectura de stderr (para debugging)
            self._stderr_task = asyncio.create_task(self._read_stderr())
            
            # Inicializar sesión MCP
            await self._initialize_mcp()
            
            logger.info("telegram-mcp process started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start telegram-mcp: {e}")
            # Intentar leer stderr si hay error
            if self._process and self._process.stderr:
                try:
                    stderr_data = await asyncio.wait_for(
                        self._process.stderr.read(1024), 
                        timeout=1.0
                    )
                    if stderr_data:
                        logger.error(f"telegram-mcp stderr: {stderr_data.decode()}")
                except:
                    pass
            self._connected = False
            return False
    
    async def _read_stderr(self):
        """Tarea para leer stderr del proceso (para debugging)."""
        try:
            while self._connected and self._process and self._process.stderr:
                line = await self._process.stderr.readline()
                if not line:
                    break
                logger.warning(f"telegram-mcp stderr: {line.decode().strip()}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Error reading stderr: {e}")
    
    async def stop(self):
        """Detener el proceso telegram-mcp."""
        self._connected = False
        
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        
        if self._stderr_task:
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass
        
        if self._process:
            logger.info("Stopping telegram-mcp process...")
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            self._process = None
        
        logger.info("telegram-mcp process stopped")
    
    async def _initialize_mcp(self):
        """Inicializar la sesión MCP."""
        init_request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "osint-aggregator",
                    "version": "1.0.0"
                }
            }
        }
        
        result = await self._send_request(init_request)
        logger.info(f"MCP initialized: {result}")
        
        # Enviar notificación de inicialización completada
        await self._send_notification({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        })
    
    def _get_next_id(self) -> int:
        """Obtener siguiente ID de request."""
        self._request_id += 1
        return self._request_id
    
    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Enviar request y esperar respuesta."""
        if not self._process or not self._process.stdin:
            raise RuntimeError("telegram-mcp process not running")
        
        request_id = request.get("id")
        if request_id is None:
            request_id = self._get_next_id()
            request["id"] = request_id
        
        # Crear future para la respuesta
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future
        
        try:
            # Enviar request
            async with self._write_lock:
                data = json.dumps(request) + "\n"
                self._process.stdin.write(data.encode())
                await self._process.stdin.drain()
            
            # Esperar respuesta con timeout
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
            
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise TimeoutError(f"Request {request_id} timed out")
        except Exception as e:
            self._pending_requests.pop(request_id, None)
            raise
    
    async def _send_notification(self, notification: Dict[str, Any]):
        """Enviar notificación (sin esperar respuesta)."""
        if not self._process or not self._process.stdin:
            return
        
        async with self._write_lock:
            data = json.dumps(notification) + "\n"
            self._process.stdin.write(data.encode())
            await self._process.stdin.drain()
    
    async def _read_responses(self):
        """Tarea para leer respuestas del proceso."""
        try:
            while self._connected and self._process and self._process.stdout:
                line = await self._process.stdout.readline()
                if not line:
                    break
                
                try:
                    response = json.loads(line.decode())
                    request_id = response.get("id")
                    
                    if request_id and request_id in self._pending_requests:
                        future = self._pending_requests.pop(request_id)
                        if not future.done():
                            if "error" in response:
                                future.set_exception(
                                    RuntimeError(response["error"].get("message", "Unknown error"))
                                )
                            else:
                                future.set_result(response.get("result", {}))
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON response: {line}")
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error reading responses: {e}")
        finally:
            self._connected = False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Llamar a una herramienta MCP.
        
        Args:
            tool_name: Nombre de la herramienta (tg_dialogs, tg_send, etc.)
            arguments: Argumentos de la herramienta
            
        Returns:
            Resultado de la herramienta
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to telegram-mcp")
        
        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        result = await self._send_request(request)
        
        # Parsear contenido
        if isinstance(result, dict) and "content" in result:
            for content in result["content"]:
                if content.get("type") == "text":
                    try:
                        return json.loads(content["text"])
                    except json.JSONDecodeError:
                        return {"text": content["text"]}
        
        return result


# =============================================================================
# HTTP Server
# =============================================================================

from aiohttp import web

class TelegramMCPHTTPServer:
    """
    Servidor HTTP que expone las operaciones de Telegram MCP.
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5001):
        self.host = host
        self.port = port
        self.mcp_service = TelegramMCPService()
        self.app = web.Application()
        self._setup_routes()
    
    def _setup_routes(self):
        """Configurar rutas HTTP."""
        self.app.router.add_get("/health", self.health_check)
        self.app.router.add_get("/status", self.get_status)
        self.app.router.add_post("/tool/{tool_name}", self.call_tool)
        
        # Endpoints específicos para compatibilidad
        self.app.router.add_get("/dialogs", self.list_dialogs)
        self.app.router.add_get("/dialog/{name}", self.get_dialog)
        self.app.router.add_post("/send", self.send_message)
        self.app.router.add_get("/me", self.get_me)
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        status = "healthy" if self.mcp_service.is_connected else "unhealthy"
        return web.json_response({
            "status": status,
            "service": "telegram-mcp",
            "timestamp": datetime.now().isoformat()
        })
    
    async def get_status(self, request: web.Request) -> web.Response:
        """Estado detallado del servicio."""
        return web.json_response({
            "connected": self.mcp_service.is_connected,
            "configured": self.mcp_service.is_configured,
            "binary_path": self.mcp_service.binary_path,
            "timestamp": datetime.now().isoformat()
        })
    
    async def call_tool(self, request: web.Request) -> web.Response:
        """Llamar a cualquier herramienta MCP."""
        tool_name = request.match_info["tool_name"]
        
        try:
            body = await request.json()
        except json.JSONDecodeError:
            body = {}
        
        try:
            result = await self.mcp_service.call_tool(tool_name, body)
            return web.json_response({"success": True, "result": result})
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return web.json_response(
                {"success": False, "error": str(e)},
                status=500
            )
    
    async def list_dialogs(self, request: web.Request) -> web.Response:
        """Listar diálogos de Telegram."""
        only_unread = request.query.get("only_unread", "false").lower() == "true"
        
        try:
            result = await self.mcp_service.call_tool("tg_dialogs", {
                "only_unread": only_unread
            })
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def get_dialog(self, request: web.Request) -> web.Response:
        """Obtener mensajes de un diálogo."""
        name = request.match_info["name"]
        offset = int(request.query.get("offset", "0"))
        
        try:
            result = await self.mcp_service.call_tool("tg_dialog", {
                "name": name,
                "offset": offset
            })
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def send_message(self, request: web.Request) -> web.Response:
        """Enviar mensaje a un diálogo."""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "Invalid JSON body"},
                status=400
            )
        
        name = body.get("name") or body.get("dialog")
        text = body.get("text") or body.get("message")
        send_direct = body.get("send", True)
        
        if not name or not text:
            return web.json_response(
                {"error": "Missing 'name' and 'text' fields"},
                status=400
            )
        
        try:
            result = await self.mcp_service.call_tool("tg_send", {
                "name": name,
                "text": text,
                "send": send_direct
            })
            return web.json_response({
                "success": True,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return web.json_response(
                {"success": False, "error": str(e)},
                status=500
            )
    
    async def get_me(self, request: web.Request) -> web.Response:
        """Obtener info de la cuenta actual."""
        try:
            result = await self.mcp_service.call_tool("tg_me", {})
            return web.json_response(result)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def start(self):
        """Iniciar el servidor."""
        # Iniciar servicio MCP
        if not await self.mcp_service.start():
            logger.warning("telegram-mcp service failed to start, running in degraded mode")
        
        # Configurar cleanup
        self.app.on_cleanup.append(self._cleanup)
        
        # Iniciar servidor HTTP
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"Telegram MCP HTTP Server running on http://{self.host}:{self.port}")
        
        return runner
    
    async def _cleanup(self, app):
        """Limpiar recursos."""
        await self.mcp_service.stop()


async def main():
    """Punto de entrada principal."""
    host = os.getenv("TELEGRAM_MCP_SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("TELEGRAM_MCP_SERVICE_PORT", "5001"))
    
    server = TelegramMCPHTTPServer(host=host, port=port)
    
    # Manejar señales
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    runner = await server.start()
    
    # Esperar señal de parada
    await stop_event.wait()
    
    # Cleanup
    await runner.cleanup()
    logger.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
