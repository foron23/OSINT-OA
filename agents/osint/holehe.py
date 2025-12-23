# =============================================================================
# Holehe Agent - Email OSINT
# =============================================================================
"""
Holehe integration agent for email OSINT.

Provides:
- HoleheAgent: Email enumeration across 100+ platforms
"""

import logging
from typing import List

from langchain_core.tools import BaseTool

from agents.base import LangChainAgent, AgentCapabilities
from tools.holehe import HoleheEmailTool

logger = logging.getLogger(__name__)


class HoleheAgent(LangChainAgent):
    """
    Agent specialized in email OSINT using Holehe.
    
    Holehe checks if an email is registered on various websites
    without alerting the target user. It's useful for:
    - Email enumeration
    - Account discovery
    - Digital footprint analysis
    """
    
    def _define_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="HoleheAgent",
            description="Email OSINT - checks email registration across 100+ platforms",
            tools=[
                "holehe_email_check",
            ],
            supported_queries=[
                "email",
                "account",
                "registration",
                "footprint",
                "identity",
            ],
        )
    
    def _get_tools(self) -> List[BaseTool]:
        """Get Holehe tools."""
        return [
            HoleheEmailTool(),
        ]
    
    def _get_system_prompt(self) -> str:
        return """You are an expert OSINT analyst specialized in email intelligence.

Your task is to investigate email addresses using Holehe tools.

Available tools:
1. **holehe_email_check** - Check if email is registered on various platforms
   - Scans 100+ websites passively
   - Does NOT alert the target user
   - Returns list of sites where email is registered
   - Helps understand digital footprint
   - Parameters:
     - email: The email address to check
     - timeout: Seconds to wait per site (default: 15)
     - only_used: Only return positive results (default: True)

Investigation methodology:

For EMAIL investigation:
1. Run holehe_email_check on the target email
2. Analyze which platforms the email is registered on
3. Categorize by type (social, professional, gaming, etc.)
4. Note patterns in registration behavior
5. Document findings with confidence levels

IMPORTANT GUIDELINES:
- This is a passive reconnaissance technique
- The target is NOT notified of the check
- Some sites may rate-limit or block requests
- Results should be verified when possible
- Consider false positives from common emails
- Respect privacy and legal boundaries

Report structure:
1. **Email Analysis Summary**
   - Email address analyzed
   - Total platforms checked
   - Total registrations found
   
2. **Registration Details**
   - Platform name
   - Category (social/professional/gaming/etc.)
   - Verification status
   
3. **Digital Footprint Assessment**
   - Online presence strength
   - Primary platform categories
   - Potential identity links
   
4. **Recommendations**
   - Further investigation areas
   - Related emails to check

Provide thorough, ethical email intelligence reports."""
