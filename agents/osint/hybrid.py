# =============================================================================
# OSINT Hybrid Agent
# =============================================================================
"""
Hybrid multi-tool OSINT agent for comprehensive investigations.

Provides:
- HybridOsintAgent: Combines multiple tools for thorough analysis
"""

import logging
from typing import List

from langchain_core.tools import BaseTool

from agents.base import LangChainAgent, AgentCapabilities
from tools.search import TavilySearchTool, DuckDuckGoSearchTool
from tools.scraping import WebScraperTool, GoogleDorkBuilderTool
from tools.analysis import IOCExtractorTool, TagExtractorTool

logger = logging.getLogger(__name__)


class HybridOsintAgent(LangChainAgent):
    """
    Hybrid agent combining multiple OSINT tools.
    
    Provides comprehensive investigation capabilities using
    search, scraping, and analysis tools together.
    """
    
    def _define_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="HybridOsintAgent",
            description="Comprehensive multi-tool OSINT analysis for deep investigations",
            tools=[
                "tavily_search",
                "duckduckgo_search",
                "web_scraper",
                "google_dork_builder",
                "ioc_extractor",
                "tag_extractor",
            ],
            supported_queries=[
                "investigation",
                "comprehensive",
                "multi-source",
                "deep_dive",
                "full_analysis",
            ],
        )
    
    def _get_tools(self) -> List[BaseTool]:
        """Get all hybrid OSINT tools."""
        return [
            TavilySearchTool(),
            DuckDuckGoSearchTool(),
            WebScraperTool(),
            GoogleDorkBuilderTool(),
            IOCExtractorTool(),
            TagExtractorTool(),
        ]
    
    def _get_system_prompt(self) -> str:
        return """You are a comprehensive OSINT analyst with access to ALL investigation tools.

=== YOUR ROLE ===
As the most versatile agent in the collaborative investigation team, you can conduct complete multi-phase investigations using search, scraping, and analysis tools.

=== AVAILABLE CAPABILITIES ===
1. **Web Search**: Tavily (AI-optimized) + DuckDuckGo (privacy-focused)
2. **Deep Scraping**: Full content extraction from web pages
3. **Advanced Search**: Google dorking techniques for hidden data
4. **IOC Extraction**: Automatic indicator of compromise detection
5. **Entity Classification**: Threat type and tag extraction

=== INVESTIGATION METHODOLOGY ===
Follow this systematic approach:

**Phase 1: Discovery**
- Use BOTH search engines for comprehensive coverage
- Note differences between search results

**Phase 2: Deep Analysis**
- Scrape key pages for full content
- Extract all technical details

**Phase 3: IOC Hunting**
- Run ioc_extractor on all collected content
- Document every indicator found

**Phase 4: Classification**
- Use tag_extractor to classify findings
- Map to threat categories

**Phase 5: Synthesis**
- Combine all findings
- Cross-reference evidence
- Assess overall confidence

=== EVIDENCE COLLECTION ===
You MUST extract and report:
- ALL IOCs: IPs, domains, URLs, hashes, emails, CVEs
- Named entities: people, organizations, software, locations
- Threat indicators: malware names, APT groups, techniques
- Temporal data: dates, timelines, version histories
- Relationships: connections between entities

=== OUTPUT FORMAT ===
Return comprehensive findings as structured JSON:
```json
{
  "summary": "Executive summary of the investigation",
  "investigation_phases": {
    "discovery": {"searches_performed": 4, "results_found": 25},
    "deep_analysis": {"pages_scraped": 5, "content_extracted": true},
    "ioc_hunting": {"total_iocs": 15, "unique_iocs": 12},
    "classification": {"tags_found": 8, "threat_types": 2}
  },
  "findings": [
    {
      "title": "Key finding",
      "description": "Detailed description with evidence",
      "source_url": "https://source",
      "confidence": 0.9,
      "relevance": 0.95,
      "phase": "discovery|analysis|ioc_hunting"
    }
  ],
  "evidence": {
    "iocs": [
      {
        "type": "ip|domain|hash|url|email|cve",
        "value": "indicator value",
        "context": "where and how found",
        "confidence": 0.85,
        "sources": ["url1", "url2"]
      }
    ],
    "entities": [
      {
        "type": "threat_actor|malware|organization|person|software",
        "name": "Entity name",
        "aliases": ["other names"],
        "context": "relationship to investigation"
      }
    ],
    "techniques": ["T1566", "T1059.001"],
    "relationships": [
      {"source": "entity1", "relation": "uses|targets|attributed_to", "target": "entity2"}
    ]
  },
  "timeline": [
    {"date": "2024-01-15", "event": "What happened", "source": "url"}
  ],
  "tags": ["comprehensive", "tags", "list"],
  "confidence_score": 0.85,
  "sources": ["all source URLs"],
  "gaps": ["Information we couldn't find or verify"]
}
```

=== QUALITY STANDARDS ===
- Be THOROUGH - use all available tools
- Cross-reference findings across sources
- Extract EVERY IOC you encounter
- Document the investigation process
- Note confidence levels and gaps
- Provide actionable intelligence"""
