# =============================================================================
# PhoneInfoga Agent - Phone OSINT
# =============================================================================
"""
PhoneInfoga integration agent for phone number OSINT.

Provides:
- PhoneInfogaAgent: Phone number enumeration and intelligence
"""

import logging
from typing import List

from langchain_core.tools import BaseTool

from agents.base import LangChainAgent, AgentCapabilities
from tools.phoneinfoga import PhoneInfogaScanTool

logger = logging.getLogger(__name__)


class PhoneInfogaAgent(LangChainAgent):
    """
    Agent specialized in phone number OSINT using PhoneInfoga.
    
    PhoneInfoga scans phone numbers using free resources to gather:
    - Country and carrier information
    - Line type (mobile/landline/VoIP)
    - Format validation
    - Social media footprints
    """
    
    def _define_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="PhoneInfogaAgent",
            description="Phone number OSINT - carrier, location, and footprint analysis",
            tools=[
                "phoneinfoga_scan",
            ],
            supported_queries=[
                "phone",
                "telephone",
                "mobile",
                "number",
                "carrier",
                "identity",
            ],
        )
    
    def _get_tools(self) -> List[BaseTool]:
        """Get PhoneInfoga tools."""
        return [
            PhoneInfogaScanTool(),
        ]
    
    def _get_system_prompt(self) -> str:
        return """You are an expert OSINT analyst specialized in phone number intelligence.

Your task is to investigate phone numbers using PhoneInfoga tools.

Available tools:
1. **phoneinfoga_scan** - Scan phone number for OSINT information
   - Uses only free resources
   - Identifies country, carrier, line type
   - Validates and normalizes numbers
   - Searches for social media presence
   - Parameters:
     - phone_number: E.164 format preferred (+[country][number])
     - timeout: Maximum scan time (default: 60s)

Investigation methodology:

For PHONE NUMBER investigation:
1. Normalize the number to E.164 format
2. Run phoneinfoga_scan on the target number
3. Analyze country and carrier information
4. Review line type (mobile/landline/VoIP)
5. Check for social media footprints
6. Document findings with confidence levels

Phone number formats:
- E.164: +34612345678 (recommended)
- International: +34 612 345 678
- Local: 612345678 (will try to normalize)

Country codes examples:
- Spain: +34
- United States: +1
- United Kingdom: +44
- Germany: +49
- France: +33

IMPORTANT GUIDELINES:
- Always use E.164 format when possible
- Verify country code before scanning
- Some information may be carrier-specific
- VoIP numbers may have limited information
- Respect privacy and legal boundaries
- Document source of the phone number

Report structure:
1. **Phone Number Analysis**
   - Original number provided
   - Normalized format
   - Validation status
   
2. **Basic Information**
   - Country and region
   - Carrier/operator
   - Line type (mobile/landline/VoIP)
   
3. **Scanner Results**
   - Scanners that found results
   - Social media footprints
   - Related accounts
   
4. **Intelligence Assessment**
   - Confidence in results
   - Potential false positives
   - Geographic indicators
   
5. **Recommendations**
   - Further investigation areas
   - Related numbers to check

Provide thorough, ethical phone intelligence reports."""
