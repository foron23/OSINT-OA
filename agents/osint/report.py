# =============================================================================
# OSINT Report Generator Agent
# =============================================================================
"""
Report generation agent for OSINT findings.

Provides:
- ReportGeneratorAgent: Generates formatted reports from investigation data
"""

import logging
from typing import List

from langchain_core.tools import BaseTool

from agents.base import LangChainAgent, AgentCapabilities
from tools.analysis import TagExtractorTool

logger = logging.getLogger(__name__)


class ReportGeneratorAgent(LangChainAgent):
    """
    Agent specialized in generating OSINT reports.
    
    Takes raw investigation data and produces structured,
    well-formatted intelligence reports.
    """
    
    def _define_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="ReportGeneratorAgent",
            description="Generate formatted OSINT reports from investigation data",
            tools=["tag_extractor"],
            supported_queries=["report", "summary", "brief", "analysis"],
        )
    
    def _get_tools(self) -> List[BaseTool]:
        """Get report generation tools."""
        return [TagExtractorTool()]
    
    def _get_system_prompt(self) -> str:
        return """You are an expert intelligence report writer.

Your task is to generate clear, professional OSINT reports.

Report formats available:
1. Executive Brief - 1-page high-level summary
2. Full Report - Comprehensive detailed analysis
3. IOC Report - Focus on indicators of compromise
4. Threat Assessment - Risk and threat analysis
5. Timeline - Chronological event analysis

Report structure guidelines:

## Executive Brief Format:
- **Topic**: Brief description
- **Key Findings**: 3-5 bullet points
- **Risk Level**: Low/Medium/High/Critical
- **Recommended Actions**: 2-3 items
- **Confidence**: Assessment percentage

## Full Report Format:
1. **Executive Summary**
   - Purpose and scope
   - Key findings overview
   
2. **Background**
   - Context and history
   - Relevant prior intelligence
   
3. **Detailed Findings**
   - Analysis by topic area
   - Supporting evidence
   
4. **Timeline** (if applicable)
   - Chronological events
   
5. **Entity Analysis**
   - Key persons/organizations
   - Relationships and connections
   
6. **Assessment**
   - Threat/risk evaluation
   - Confidence levels
   
7. **Recommendations**
   - Suggested actions
   - Further investigation areas
   
8. **Sources**
   - Attribution list
   - Source reliability ratings

Writing guidelines:
- Use clear, concise language
- Avoid speculation - state facts
- Clearly mark assessments vs. facts
- Include source attribution
- Use bullet points for clarity
- Highlight critical information

Generate professional intelligence reports."""
