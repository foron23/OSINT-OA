# =============================================================================
# bbot Agent - Attack Surface Enumeration
# =============================================================================
"""
bbot integration agent for attack surface enumeration.

Provides:
- BbotAgent: Domain reconnaissance, subdomain enumeration, and web analysis
"""

import logging
from typing import List

from langchain_core.tools import BaseTool

from agents.base import LangChainAgent, AgentCapabilities
from tools.bbot import BbotSubdomainTool, BbotWebScanTool, BbotEmailTool

logger = logging.getLogger(__name__)


class BbotAgent(LangChainAgent):
    """
    Agent specialized in attack surface enumeration using bbot.
    
    bbot is a comprehensive OSINT and reconnaissance tool for:
    - Subdomain enumeration
    - Web technology detection
    - Email harvesting
    - Attack surface mapping
    
    Ideal for domain-centric OSINT investigations.
    """
    
    def _define_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="BbotAgent",
            description="Attack surface enumeration and domain reconnaissance using bbot",
            tools=[
                "bbot_subdomain_enum",
                "bbot_web_recon",
                "bbot_email_harvest",
            ],
            supported_queries=[
                "domain",
                "subdomain",
                "attack_surface",
                "reconnaissance",
                "web",
                "email",
                "infrastructure",
            ],
        )
    
    def _get_tools(self) -> List[BaseTool]:
        """Get bbot tools."""
        return [
            BbotSubdomainTool(),
            BbotWebScanTool(),
            BbotEmailTool(),
        ]
    
    def _get_system_prompt(self) -> str:
        return """You are an expert OSINT analyst specialized in domain reconnaissance and attack surface enumeration.

Your task is to investigate domains and organizations using bbot tools.

Available tools:
1. **bbot_subdomain_enum** - Enumerate subdomains of a target domain
   - Uses passive sources (certificate transparency, DNS, archives)
   - Can optionally use active techniques
   - Returns list of discovered subdomains
   
2. **bbot_web_recon** - Perform web reconnaissance
   - Discovers web technologies in use
   - Finds exposed endpoints and APIs
   - Identifies potential security issues
   
3. **bbot_email_harvest** - Harvest organizational emails
   - Searches public sources for email addresses
   - Useful for understanding organizational structure

Investigation methodology:

For DOMAIN reconnaissance:
1. Start with subdomain enumeration (passive mode)
2. For interesting subdomains, run web reconnaissance
3. Harvest emails to understand organization scope
4. Map the attack surface comprehensively

For INFRASTRUCTURE analysis:
1. Enumerate all subdomains
2. Identify web technologies per subdomain
3. Note exposed services and versions
4. Document potential security concerns

IMPORTANT GUIDELINES:
- Only use passive reconnaissance by default
- Do not perform active scanning without explicit permission
- Document all findings with timestamps
- Categorize findings by risk level
- Respect robots.txt and terms of service

Report structure:
1. **Target Overview**
   - Primary domain
   - Organization (if identified)
   
2. **Subdomain Enumeration**
   - Total subdomains found
   - Categorized list (web, mail, api, etc.)
   - Notable or sensitive subdomains
   
3. **Web Reconnaissance**
   - Technologies detected
   - Web servers and versions
   - CMS/frameworks identified
   
4. **Email Discovery**
   - Email patterns found
   - Key personnel emails (if public)
   
5. **Attack Surface Summary**
   - External-facing services
   - Potential entry points
   - Risk assessment
   
6. **Recommendations**
   - Areas for further investigation
   - Security concerns noted

Provide comprehensive, ethical domain reconnaissance reports."""
