# =============================================================================
# OSINT News Aggregator - Tools Module
# =============================================================================
"""
LangChain Tools for OSINT operations.

This module provides all tools that agents can use:
- Search tools (Tavily, DuckDuckGo, Google Dorking)
- Scraping tools (Web content extraction)
- Analysis tools (IOC extraction, tagging)
- Maigret tools (Username enumeration)
- bbot tools (Attack surface enumeration)
- Holehe tools (Email registration check)
- Amass tools (Subdomain enumeration)
- PhoneInfoga tools (Phone number OSINT)
- Telegram tools (MCP-based messaging)

Usage:
    from tools import get_all_tools, get_search_tools
    
    # Get all available tools
    all_tools = get_all_tools()
    
    # Get specific tool categories
    search_tools = get_search_tools()
"""

from tools.base import ToolInput, WebSearchInput, UrlInput, TextAnalysisInput
from tools.search import (
    TavilySearchTool,
    DuckDuckGoSearchTool,
    GoogleDorkBuilderTool,
)
from tools.scraping import WebScraperTool
from tools.analysis import (
    IOCExtractorTool,
    TagExtractorTool,
)

# Modern OSINT tools (replacing OSRFramework)
from tools.maigret import (
    MaigretUsernameTool,
    MaigretReportTool,
)
from tools.bbot import (
    BbotSubdomainTool,
    BbotWebScanTool,
    BbotEmailTool,
)

# New OSINT tools
from tools.holehe import (
    HoleheEmailTool,
)
from tools.amass import (
    AmassEnumTool,
    AmassIntelTool,
)
from tools.phoneinfoga import (
    PhoneInfogaScanTool,
)

from tools.telegram import (
    TelegramMCPSendTool,
    TelegramMCPPublishReportTool,
    TelegramMCPListDialogsTool,
    TelegramPublishTool,
)


def get_all_tools():
    """Get all available OSINT tools."""
    return [
        TavilySearchTool(),
        DuckDuckGoSearchTool(),
        GoogleDorkBuilderTool(),
        WebScraperTool(),
        IOCExtractorTool(),
        TagExtractorTool(),
        MaigretUsernameTool(),
        BbotSubdomainTool(),
        HoleheEmailTool(),
        AmassEnumTool(),
        PhoneInfogaScanTool(),
        TelegramMCPSendTool(),
    ]


def get_search_tools():
    """Get web search tools."""
    return [
        TavilySearchTool(),
        DuckDuckGoSearchTool(),
        GoogleDorkBuilderTool(),
    ]


def get_analysis_tools():
    """Get analysis and extraction tools."""
    return [
        IOCExtractorTool(),
        TagExtractorTool(),
        WebScraperTool(),
    ]


def get_maigret_tools():
    """Get Maigret username OSINT tools."""
    return [
        MaigretUsernameTool(),
        MaigretReportTool(),
    ]


def get_bbot_tools():
    """Get bbot attack surface enumeration tools."""
    return [
        BbotSubdomainTool(),
        BbotWebScanTool(),
        BbotEmailTool(),
    ]


def get_holehe_tools():
    """Get Holehe email OSINT tools."""
    return [
        HoleheEmailTool(),
    ]


def get_amass_tools():
    """Get Amass subdomain enumeration tools."""
    return [
        AmassEnumTool(),
        AmassIntelTool(),
    ]


def get_phoneinfoga_tools():
    """Get PhoneInfoga phone number OSINT tools."""
    return [
        PhoneInfogaScanTool(),
    ]


def get_identity_tools():
    """Get all identity/OSINT tools (Maigret + bbot + Holehe + PhoneInfoga)."""
    return get_maigret_tools() + get_bbot_tools() + get_holehe_tools() + get_phoneinfoga_tools()


def get_domain_tools():
    """Get all domain reconnaissance tools (bbot + Amass)."""
    return get_bbot_tools() + get_amass_tools()


def get_telegram_mcp_tools():
    """Get Telegram MCP tools."""
    return [
        TelegramMCPSendTool(),
        TelegramMCPPublishReportTool(),
        TelegramMCPListDialogsTool(),
    ]


__all__ = [
    # Base
    'ToolInput',
    'WebSearchInput', 
    'UrlInput',
    'TextAnalysisInput',
    # Search
    'TavilySearchTool',
    'DuckDuckGoSearchTool',
    'GoogleDorkBuilderTool',
    # Scraping
    'WebScraperTool',
    # Analysis
    'IOCExtractorTool',
    'TagExtractorTool',
    # Maigret (username OSINT)
    'MaigretUsernameTool',
    'MaigretReportTool',
    # bbot (attack surface)
    'BbotSubdomainTool',
    'BbotWebScanTool',
    'BbotEmailTool',
    # Holehe (email OSINT)
    'HoleheEmailTool',
    # Amass (subdomain enumeration)
    'AmassEnumTool',
    'AmassIntelTool',
    # PhoneInfoga (phone OSINT)
    'PhoneInfogaScanTool',
    # Telegram
    'TelegramMCPSendTool',
    'TelegramMCPPublishReportTool',
    'TelegramMCPListDialogsTool',
    'TelegramPublishTool',
    # Utility functions
    'get_all_tools',
    'get_search_tools',
    'get_analysis_tools',
    'get_maigret_tools',
    'get_bbot_tools',
    'get_holehe_tools',
    'get_amass_tools',
    'get_phoneinfoga_tools',
    'get_identity_tools',
    'get_domain_tools',
    'get_telegram_mcp_tools',
]
