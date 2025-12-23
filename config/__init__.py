# =============================================================================
# OSINT OA - Configuration Module
# =============================================================================
"""
Centralized configuration management.

Usage:
    from config import settings
    # or for backward compatibility:
    from config import config
    
    # Access configuration
    api_key = settings.OPENAI_API_KEY
    db_path = settings.DATABASE_PATH
"""

from config.settings import settings, Settings

# Backward compatibility: alias settings as config
config = settings

__all__ = ['settings', 'Settings', 'config']
