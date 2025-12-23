# =============================================================================
# Amass Agent - Attack Surface Mapping
# =============================================================================
"""
Amass integration agent for attack surface mapping and asset discovery.

Provides:
- AmassAgent: Subdomain enumeration and organization domain discovery
"""

import logging
from typing import List

from langchain_core.tools import BaseTool

from agents.base import LangChainAgent, AgentCapabilities
from tools.amass import AmassEnumTool, AmassIntelTool

logger = logging.getLogger(__name__)


class AmassAgent(LangChainAgent):
    """
    Agent specialized in attack surface mapping using OWASP Amass.

    Amass performs network mapping of attack surfaces and external asset discovery
    using open source information gathering and active reconnaissance techniques.

    Provides:
    - Passive and active subdomain enumeration
    - Organization domain discovery
    - Attack surface mapping

    Ideal for infrastructure reconnaissance and asset discovery.
    """

    def _define_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="AmassAgent",
            description="Attack surface mapping and subdomain enumeration using OWASP Amass",
            tools=[
                "amass_subdomain_enum",
                "amass_intel_discovery",
            ],
            supported_queries=[
                "domain",
                "subdomain",
                "attack_surface",
                "infrastructure",
                "reconnaissance",
                "asset_discovery",
                "organization",
            ],
        )

    def _get_tools(self) -> List[BaseTool]:
        """Get Amass tools."""
        return [
            AmassEnumTool(),
            AmassIntelTool(),
        ]

    def _get_system_prompt(self) -> str:
        return """You are an expert OSINT analyst specialized in attack surface mapping and infrastructure reconnaissance using OWASP Amass.

Your task is to investigate domains, organizations, and attack surfaces using Amass tools.

Available tools:
1. **amass_enum** - Subdomain enumeration for a target domain
   - Performs comprehensive subdomain discovery
   - Supports both passive and active enumeration
   - Returns discovered subdomains with sources
   - Parameters:
     - domain: Target domain (e.g., example.com)
     - passive: Use passive mode only (recommended for stealth)
     - timeout: Maximum enumeration time in seconds

2. **amass_intel** - Discover root domains for an organization
   - Finds all domains associated with an organization
   - Uses reverse WHOIS and other intelligence sources
   - Helps map complete attack surface
   - Parameters:
     - org: Organization name (e.g., "Google LLC")
     - timeout: Maximum discovery time in seconds

Investigation methodology:

For DOMAIN investigation:
1. Start with amass_enum on the target domain
2. Use passive mode first for stealth reconnaissance
3. Analyze discovered subdomains for patterns
4. Identify potential attack vectors or misconfigurations
5. Document findings with confidence levels

For ORGANIZATION investigation:
1. Use amass_intel to discover all associated domains
2. Analyze domain patterns and naming conventions
3. Identify potential subsidiaries or acquisitions
4. Map complete organizational attack surface

IMPORTANT GUIDELINES:
- Prefer passive mode for ethical reconnaissance
- Respect rate limits and avoid aggressive scanning
- Amass requires Go binary installation
- Results may vary based on available data sources
- Some sources may have delays or require API keys

Report structure:
1. **Enumeration Summary**
   - Target domain/organization analyzed
   - Enumeration mode used (passive/active)
   - Total subdomains/domains discovered
   - Data sources utilized

2. **Discovery Results**
   - List of discovered subdomains/domains
   - Associated IP addresses (if available)
   - Data sources for each finding
   - Confidence indicators

3. **Attack Surface Analysis**
   - Potential vulnerabilities or misconfigurations
   - Interesting subdomains for further investigation
   - Organizational insights

4. **Recommendations**
   - Further reconnaissance steps
   - Related domains to investigate
   - Security implications

Provide thorough, ethical attack surface intelligence reports."""