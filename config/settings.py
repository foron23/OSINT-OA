# =============================================================================
# OSINT News Aggregator - Configuration Settings
# =============================================================================
"""
Application settings loaded from environment variables.

All configuration is centralized here for easy maintenance.
Environment variables are loaded from .env file using python-dotenv.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Settings:
    """
    Application configuration container.
    
    All settings are loaded from environment variables with sensible defaults.
    Use the global `settings` instance instead of creating new instances.
    """
    
    # =========================================================================
    # Path Configuration
    # =========================================================================
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent.absolute())
    
    @property
    def DATA_DIR(self) -> Path:
        """Directory for data files (database, reports, etc.)."""
        return self.BASE_DIR / "data"
    
    @property
    def BIN_DIR(self) -> Path:
        """Directory for binary executables."""
        return self.BASE_DIR / "bin"
    
    # =========================================================================
    # Flask Configuration
    # =========================================================================
    @property
    def FLASK_ENV(self) -> str:
        return os.getenv("FLASK_ENV", "development")
    
    @property
    def FLASK_DEBUG(self) -> bool:
        return os.getenv("FLASK_DEBUG", "1") == "1"
    
    @property
    def SECRET_KEY(self) -> str:
        return os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    @property
    def HOST(self) -> str:
        return os.getenv("HOST", "0.0.0.0")
    
    @property
    def PORT(self) -> int:
        return int(os.getenv("PORT", "5000"))
    
    # =========================================================================
    # Database Configuration
    # =========================================================================
    @property
    def DATABASE_PATH(self) -> str:
        default = str(self.DATA_DIR / "osint.db")
        return os.getenv("DATABASE_PATH", default)
    
    # =========================================================================
    # OpenAI Configuration
    # =========================================================================
    @property
    def OPENAI_API_KEY(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")
    
    @property
    def OPENAI_MODEL(self) -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # =========================================================================
    # Telegram Configuration
    # =========================================================================
    @property
    def TELEGRAM_BOT_TOKEN(self) -> str:
        return os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    @property
    def TELEGRAM_CHAT_ID(self) -> str:
        return os.getenv("TELEGRAM_CHAT_ID", "")
    
    @property
    def TELEGRAM_APP_ID(self) -> str:
        """Telegram API App ID (also available as TG_APP_ID)."""
        return os.getenv("TELEGRAM_APP_ID", "") or os.getenv("TG_APP_ID", "")
    
    @property
    def TELEGRAM_API_HASH(self) -> str:
        """Telegram API Hash (also available as TG_API_HASH)."""
        return os.getenv("TELEGRAM_API_HASH", "") or os.getenv("TG_API_HASH", "")
    
    @property
    def TELEGRAM_TARGET_DIALOG(self) -> str:
        """Default Telegram dialog for publishing (e.g., cht[123456])."""
        return os.getenv("TELEGRAM_TARGET_DIALOG", "")
    
    # =========================================================================
    # Search API Configuration
    # =========================================================================
    @property
    def TAVILY_API_KEY(self) -> str:
        return os.getenv("TAVILY_API_KEY", "")
    
    @property
    def GOOGLE_API_KEY(self) -> str:
        return os.getenv("GOOGLE_API_KEY", "")
    
    @property
    def GOOGLE_CSE_ID(self) -> str:
        return os.getenv("GOOGLE_CSE_ID", "")
    
    # =========================================================================
    # LangSmith Configuration (Tracing)
    # =========================================================================
    @property
    def LANGSMITH_TRACING(self) -> bool:
        return os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    
    @property
    def LANGSMITH_API_KEY(self) -> str:
        return os.getenv("LANGSMITH_API_KEY", "")
    
    @property
    def LANGSMITH_PROJECT(self) -> str:
        return os.getenv("LANGSMITH_PROJECT", "osint-agents")
    
    # =========================================================================
    # External Tools Configuration
    # =========================================================================
    @property
    def RECON_NG_PATH(self) -> str:
        return os.getenv("RECON_NG_PATH", "recon-ng")
    
    @property
    def SPIDERFOOT_PATH(self) -> str:
        return os.getenv("SPIDERFOOT_PATH", "sf.py")
    
    @property
    def OSINT_TOOL_PATH(self) -> str:
        return os.getenv("OSINT_TOOL_PATH", "osint-tool")
    
    @property
    def TELEGRAM_MCP_PATH(self) -> str:
        """Path to telegram-mcp binary (juananpe fork with send-direct)."""
        default = str(self.BIN_DIR / "telegram-mcp")
        return os.getenv("TELEGRAM_MCP_PATH", default)
    
    # =========================================================================
    # Rate Limits and Timeouts
    # =========================================================================
    @property
    def DEFAULT_TIMEOUT(self) -> int:
        return int(os.getenv("DEFAULT_TIMEOUT", "30"))
    
    @property
    def MAX_CONCURRENT_TASKS(self) -> int:
        return int(os.getenv("MAX_CONCURRENT_TASKS", "5"))
    
    @property
    def RATE_LIMIT_REQUESTS_PER_MINUTE(self) -> int:
        return int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
    
    # =========================================================================
    # Security Configuration
    # =========================================================================
    @property
    def ALLOWED_SCOPE_DOMAINS(self) -> List[str]:
        domains = os.getenv("ALLOWED_SCOPE_DOMAINS", "")
        return [d.strip() for d in domains.split(",") if d.strip()]
    
    @property
    def MAX_RESULTS_PER_QUERY(self) -> int:
        return int(os.getenv("MAX_RESULTS_PER_QUERY", "100"))
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    def ensure_data_dir(self) -> None:
        """Ensure the data directory exists."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    def ensure_bin_dir(self) -> None:
        """Ensure the bin directory exists."""
        self.BIN_DIR.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of warnings.
        
        Returns:
            List of warning messages for missing or invalid config.
        """
        warnings = []
        
        if not self.OPENAI_API_KEY:
            warnings.append("OPENAI_API_KEY not set - LangChain agents will not function")
        
        if not self.TAVILY_API_KEY:
            warnings.append("TAVILY_API_KEY not set - Tavily search disabled, using DuckDuckGo")
        
        if not self.TELEGRAM_APP_ID or not self.TELEGRAM_API_HASH:
            warnings.append("Telegram API credentials not set - Telegram features disabled")
        
        if not self.TELEGRAM_TARGET_DIALOG:
            warnings.append("TELEGRAM_TARGET_DIALOG not set - Telegram publishing disabled")
        
        return warnings
    
    def is_telegram_configured(self) -> bool:
        """Check if Telegram is fully configured."""
        return bool(
            self.TELEGRAM_APP_ID and 
            self.TELEGRAM_API_HASH and 
            self.TELEGRAM_TARGET_DIALOG
        )
    
    def is_openai_configured(self) -> bool:
        """Check if OpenAI is configured."""
        return bool(self.OPENAI_API_KEY)


# =============================================================================
# Global Settings Instance
# =============================================================================

settings = Settings()

# Backward compatibility alias
config = settings
