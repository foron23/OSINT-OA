# =============================================================================
# OSINT Agents Package
# =============================================================================
"""
OSINT-specialized agents for the news aggregator.

Modules:
- search: Search-based agents (Tavily, DuckDuckGo, Google Dorking)
- analysis: Analysis agents (Web Scraper, Threat Intel, IOC Analysis)
- hybrid: Multi-tool hybrid agent
- report: Report generation agents
- maigret: Username OSINT agent (replaces OSRFramework)
- bbot: Attack surface enumeration agent
"""

from agents.osint.search import (
    TavilySearchAgent,
    DuckDuckGoSearchAgent,
    GoogleDorkingAgent,
)

from agents.osint.analysis import (
    WebScraperAgent,
    ThreatIntelAgent,
    IOCAnalysisAgent,
)

from agents.osint.hybrid import HybridOsintAgent
from agents.osint.report import ReportGeneratorAgent

# Modern OSINT agents (replacing OSRFramework)
from agents.osint.maigret import MaigretAgent
from agents.osint.bbot import BbotAgent

__all__ = [
    # Search agents
    "TavilySearchAgent",
    "DuckDuckGoSearchAgent",
    "GoogleDorkingAgent",
    # Analysis agents
    "WebScraperAgent",
    "ThreatIntelAgent",
    "IOCAnalysisAgent",
    # Hybrid agent
    "HybridOsintAgent",
    # Report agent
    "ReportGeneratorAgent",
    # Modern OSINT agents
    "MaigretAgent",
    "BbotAgent",
]
