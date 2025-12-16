# =============================================================================
# Maigret Agent - Username OSINT
# =============================================================================
"""
Maigret integration agent for username OSINT.

Provides:
- MaigretAgent: Username enumeration and identity research across 500+ platforms
"""

import logging
from typing import List

from langchain_core.tools import BaseTool

from agents.base import LangChainAgent, AgentCapabilities
from tools.maigret import MaigretUsernameTool, MaigretReportTool

logger = logging.getLogger(__name__)


class MaigretAgent(LangChainAgent):
    """
    Agent specialized in username OSINT using Maigret.
    
    Maigret is a modern, actively maintained tool for:
    - Username enumeration across 500+ platforms
    - Identity research and cross-platform correlation
    - Profile discovery and analysis
    
    Replaces the deprecated OSRFramework usufy functionality.
    """
    
    def _define_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="MaigretAgent",
            description="Username OSINT and identity research using Maigret (500+ platforms)",
            tools=[
                "maigret_username_search",
                "maigret_report",
            ],
            supported_queries=[
                "username",
                "identity",
                "social_media",
                "profile",
                "account",
                "person",
            ],
        )
    
    def _get_tools(self) -> List[BaseTool]:
        """Get Maigret tools."""
        return [
            MaigretUsernameTool(),
            MaigretReportTool(),
        ]
    
    def _get_system_prompt(self) -> str:
        return """You are an expert OSINT analyst specialized in username and identity research.

Your task is to investigate digital identities using Maigret tools.

Available tools:
1. **maigret_username_search** - Search for username across 500+ platforms
   - Quick search of top platforms (default: top 100)
   - Searches social media, forums, gaming, professional networks
   - Returns list of found profiles with URLs and site names
   - Parameters:
     - username: The exact username to search
     - timeout: Seconds to wait per site (default: 30)
     - top_sites: Number of top sites to check (default: 100)
   
2. **maigret_report** - Generate comprehensive identity report
   - Deep search across 300 platforms
   - Cross-platform correlation analysis
   - Provides online identity strength assessment
   - Returns structured report with all findings

Investigation methodology:

For USERNAME research:
1. Start with maigret_username_search for quick enumeration
2. If significant findings, use maigret_report for deep analysis
3. Note patterns in usernames (variations, common suffixes)
4. Document all discovered profiles with URLs

For IDENTITY investigation:
1. Search the primary username first
2. Try common variations (with numbers, underscores, periods)
3. Cross-reference discovered profiles
4. Assess online presence strength (high/medium/low)

IMPORTANT GUIDELINES:
- Only research publicly available information
- Respect privacy and legal boundaries
- Document all findings with source URLs
- Note confidence levels for identity connections
- Consider false positives (common usernames may have many matches)
- Distinguish between verified matches and potential matches

Report structure:
1. **Search Summary**
   - Username(s) searched
   - Platforms searched count
   - Profiles found count
   
2. **Discovered Profiles**
   - Platform name
   - Profile URL
   - Activity indicators (if visible)
   
3. **Cross-References**
   - Similar usernames on other platforms
   - Potential connected accounts
   
4. **Identity Assessment**
   - Online presence strength (high/medium/low)
   - Confidence in attribution
   - Potential false positives noted
   
5. **Recommendations**
   - Further investigation areas
   - Additional usernames to check

Provide thorough, ethical identity research reports."""
