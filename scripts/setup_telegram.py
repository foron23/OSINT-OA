#!/usr/bin/env python3
# =============================================================================
# Telegram Setup Script (Telethon-based)
# =============================================================================
"""
Script interactivo para configurar la autenticación de Telegram.

Este script ahora usa Telethon directamente (sin MCP binary).

Uso dentro del contenedor Docker:
    docker-compose -f docker-compose.prod.yml exec osint-oa \
        python scripts/setup_telegram.py

Uso local:
    python scripts/setup_telegram.py
"""

import os
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Redirect to the Telethon-based setup
from scripts.setup_telegram_telethon import main

if __name__ == "__main__":
    main()
