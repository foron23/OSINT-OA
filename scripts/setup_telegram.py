#!/usr/bin/env python3
# =============================================================================
# Telegram MCP Setup Script
# =============================================================================
"""
Script interactivo para configurar la autenticación de Telegram MCP.

Uso dentro del contenedor Docker:
    docker-compose -f docker-compose.prod.yml exec osint-aggregator \
        python scripts/setup_telegram.py

Uso local:
    python scripts/setup_telegram.py
"""

import os
import sys
import subprocess
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_banner():
    """Mostrar banner inicial."""
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                     TELEGRAM MCP SETUP                                    ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  Este script te guiará para configurar la autenticación de Telegram.     ║
║                                                                           ║
║  Necesitarás:                                                             ║
║  1. Credenciales de API de Telegram (my.telegram.org/apps)                ║
║  2. Acceso a tu cuenta de Telegram para recibir código de verificación   ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)


def check_credentials():
    """Verificar que las credenciales están configuradas."""
    app_id = os.getenv("TELEGRAM_APP_ID") or os.getenv("TG_APP_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH") or os.getenv("TG_API_HASH")
    
    if not app_id or not api_hash:
        print("\n❌ ERROR: Credenciales de Telegram no configuradas.")
        print("\n   Configura en tu archivo .env:")
        print("   TELEGRAM_APP_ID=tu_app_id")
        print("   TELEGRAM_API_HASH=tu_api_hash")
        print("\n   Obtener en: https://my.telegram.org/apps")
        return None, None
    
    print(f"\n✅ Credenciales encontradas:")
    print(f"   App ID: {app_id[:4]}{'*' * (len(app_id) - 4)}")
    print(f"   API Hash: {api_hash[:6]}{'*' * (len(api_hash) - 6)}")
    
    return app_id, api_hash


def check_binary():
    """Verificar que el binario de Telegram MCP existe."""
    mcp_path = os.getenv("TELEGRAM_MCP_PATH", "")
    
    # Intentar encontrar el binario
    possible_paths = [
        mcp_path,
        "/app/bin/telegram-mcp",
        str(Path(__file__).parent.parent / "bin" / "telegram-mcp"),
        "./bin/telegram-mcp"
    ]
    
    for path in possible_paths:
        if path and os.path.exists(path) and os.access(path, os.X_OK):
            print(f"\n✅ Binario de Telegram MCP encontrado: {path}")
            return path
    
    print("\n❌ ERROR: Binario de Telegram MCP no encontrado.")
    print("   Verifica que bin/telegram-mcp existe y es ejecutable.")
    return None


def run_telegram_auth(binary_path, app_id, api_hash):
    """Ejecutar el proceso de autenticación de Telegram."""
    session_path = os.getenv("TELEGRAM_SESSION_PATH", "./data/telegram-session")
    
    # Crear directorio de sesión si no existe
    os.makedirs(session_path, exist_ok=True)
    
    print(f"\n📂 Directorio de sesión: {session_path}")
    print("\n🔐 Iniciando proceso de autenticación...")
    print("   (Sigue las instrucciones en pantalla)\n")
    print("-" * 60)
    
    # Configurar variables de entorno
    env = os.environ.copy()
    env["TG_APP_ID"] = app_id
    env["TG_API_HASH"] = api_hash
    
    try:
        # Ejecutar el binario en modo interactivo
        # El binario telegram-mcp debería manejar la autenticación
        process = subprocess.run(
            [binary_path],
            env=env,
            cwd=session_path,
            timeout=300  # 5 minutos de timeout
        )
        
        if process.returncode == 0:
            print("\n" + "-" * 60)
            print("\n✅ Autenticación completada exitosamente!")
            print(f"   Sesión guardada en: {session_path}")
        else:
            print("\n" + "-" * 60)
            print(f"\n⚠️  El proceso terminó con código: {process.returncode}")
            
    except subprocess.TimeoutExpired:
        print("\n⏱️  Timeout - el proceso tardó demasiado.")
    except Exception as e:
        print(f"\n❌ Error ejecutando el binario: {e}")


def verify_session():
    """Verificar si hay una sesión válida."""
    session_path = os.getenv("TELEGRAM_SESSION_PATH", "./data/telegram-session")
    session_file = Path(session_path) / "session.json"
    
    if session_file.exists():
        print(f"\n✅ Archivo de sesión encontrado: {session_file}")
        return True
    
    # Buscar otros posibles archivos de sesión
    session_dir = Path(session_path)
    if session_dir.exists():
        files = list(session_dir.glob("*"))
        if files:
            print(f"\n✅ Archivos de sesión encontrados: {[f.name for f in files]}")
            return True
    
    print("\n⚠️  No se encontró archivo de sesión existente.")
    return False


def test_connection():
    """Probar la conexión con Telegram."""
    try:
        from integrations.telegram.mcp_client import TelegramMCPClient
        
        print("\n🔍 Probando conexión con Telegram...")
        
        client = TelegramMCPClient()
        
        if not client.is_configured:
            print("❌ Cliente no configurado.")
            return False
        
        print("✅ Cliente de Telegram MCP configurado correctamente.")
        return True
        
    except ImportError as e:
        print(f"\n⚠️  No se pudo importar el cliente: {e}")
        return False
    except Exception as e:
        print(f"\n⚠️  Error probando conexión: {e}")
        return False


def main():
    """Función principal."""
    print_banner()
    
    # Verificar credenciales
    app_id, api_hash = check_credentials()
    if not app_id:
        sys.exit(1)
    
    # Verificar binario
    binary_path = check_binary()
    if not binary_path:
        sys.exit(1)
    
    # Verificar si ya hay sesión
    has_session = verify_session()
    
    if has_session:
        print("\n¿Qué deseas hacer?")
        print("  1. Usar sesión existente (probar conexión)")
        print("  2. Re-autenticar (crear nueva sesión)")
        print("  3. Salir")
        
        choice = input("\nOpción [1]: ").strip() or "1"
        
        if choice == "1":
            test_connection()
            return
        elif choice == "3":
            print("\n👋 Saliendo...")
            return
    
    # Ejecutar autenticación
    print("\n⚠️  IMPORTANTE:")
    print("   - Recibirás un código de verificación en Telegram")
    print("   - Asegúrate de tener acceso a tu cuenta de Telegram")
    
    proceed = input("\n¿Continuar con la autenticación? [y/N]: ").strip().lower()
    
    if proceed in ["y", "yes", "s", "si"]:
        run_telegram_auth(binary_path, app_id, api_hash)
        test_connection()
    else:
        print("\n👋 Autenticación cancelada.")


if __name__ == "__main__":
    main()
