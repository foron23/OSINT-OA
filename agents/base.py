# =============================================================================
# OSINT Agentic Operations - Base Agent Classes
# =============================================================================
"""
Base classes for LangGraph OSINT agents.

Provides:
- AgentCapabilities: Describes agent capabilities
- LangChainAgent: Abstract base class for all agents (LangGraph-based)
- Evidence extraction and IOC collection utilities
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime

from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# Type checking only imports (avoid circular dependencies at runtime)
if TYPE_CHECKING:
    from db.models import OsintResult, ItemType

logger = logging.getLogger(__name__)


def _get_osint_models():
    """Lazy import of OsintResult and ItemType to avoid circular imports."""
    from db.models import OsintResult, ItemType
    return OsintResult, ItemType


# =============================================================================
# Agent Capabilities
# =============================================================================

@dataclass
class AgentCapabilities:
    """
    Describes what an agent can do.
    
    Used for agent discovery and task assignment by the orchestrator.
    """
    name: str
    description: str
    supported_queries: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    requires_api_key: bool = False
    api_key_env_var: str = ""
    uses_react: bool = True
    rate_limit_per_minute: int = 60
    max_results: int = 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "supported_queries": self.supported_queries,
            "tools": self.tools,
            "requires_api_key": self.requires_api_key,
            "uses_react": self.uses_react,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "max_results": self.max_results,
        }


# =============================================================================
# Base LangChain Agent
# =============================================================================

class LangChainAgent(ABC):
    """
    Abstract base class for all LangChain OSINT agents.
    
    Implements the ReAct (Reasoning + Acting) pattern using LangGraph.
    All specialized agents inherit from this class.
    """
    
    def __init__(self):
        """Initialize the agent."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self._capabilities = self._define_capabilities()
        self.llm: Optional[ChatOpenAI] = None
        self.tools: List[BaseTool] = []
        self.agent = None
        self._initialize()
    
    @property
    def name(self) -> str:
        """Return the agent name."""
        return self._capabilities.name
    
    @property
    def capabilities(self) -> AgentCapabilities:
        """Return agent capabilities."""
        return self._capabilities
    
    @abstractmethod
    def _define_capabilities(self) -> AgentCapabilities:
        """
        Define and return agent capabilities.
        
        Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    def _get_tools(self) -> List[BaseTool]:
        """
        Return list of tools for this agent.
        
        Must be implemented by subclasses.
        """
        pass
    
    def _get_system_prompt(self) -> str:
        """
        Get the system prompt for the ReAct agent.
        
        Can be overridden by subclasses for customization.
        """
        tool_list = '\n'.join(
            f'- {t.name}: {t.description[:100]}...' 
            for t in self.tools
        )
        
        return f"""You are an expert OSINT (Open Source Intelligence) analyst agent participating in a collaborative multi-agent investigation.

Your name: {self.name}
Your role: {self._capabilities.description}

=== MISSION ===
You are part of an OSINT Agentic Operations system where multiple specialized agents collaborate to conduct thorough investigations. Your findings will be synthesized with other agents' discoveries to build comprehensive intelligence reports.

=== WORKFLOW (ReAct Pattern) ===
1. THINK: Analyze the query and plan your investigation approach
2. ACT: Use your tools strategically to gather intelligence
3. OBSERVE: Analyze results and extract key evidence
4. REPEAT: Continue until you have sufficient high-quality intelligence
5. RESPOND: Return structured findings with extracted IOCs and evidence

=== AVAILABLE TOOLS ===
{tool_list}

=== EVIDENCE COLLECTION REQUIREMENTS ===
You MUST actively extract and report:

**Indicators of Compromise (IOCs):**
- IP addresses (IPv4/IPv6)
- Domain names and URLs
- File hashes (MD5, SHA1, SHA256)
- Email addresses
- CVE identifiers
- Cryptocurrency addresses
- Usernames/handles

**Intelligence Artifacts:**
- Threat actor names and aliases
- Malware family names
- Attack techniques (MITRE ATT&CK)
- Vulnerable software/versions
- Geographic locations
- Timestamps and dates
- Organization names
- Key relationships between entities

=== OUTPUT FORMAT ===
Always structure your final response as JSON:
```json
{{
  "summary": "Brief summary of findings (2-3 sentences)",
  "findings": [
    {{
      "title": "Finding title",
      "description": "Detailed description",
      "source_url": "URL where found",
      "confidence": 0.0-1.0,
      "relevance": 0.0-1.0
    }}
  ],
  "evidence": {{
    "iocs": [
      {{"type": "ip|domain|url|hash|email|cve|handle", "value": "...", "context": "where/how found"}}
    ],
    "entities": [
      {{"type": "threat_actor|malware|organization|person|location", "name": "...", "context": "..."}}
    ],
    "techniques": ["MITRE ATT&CK IDs if applicable"]
  }},
  "tags": ["relevant", "classification", "tags"],
  "confidence_score": 0.0-1.0,
  "sources": ["list of source URLs"]
}}
```

=== COLLABORATION NOTES ===
- Your output will be combined with other agents' findings
- Be specific and factual - avoid speculation
- Rate your confidence honestly
- Include source URLs for verification
- Flag any conflicting information found"""
    
    def _get_model_name(self) -> str:
        """Get the OpenAI model name from config."""
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    def _initialize(self):
        """Initialize the LangChain agent."""
        api_key = os.getenv("OPENAI_API_KEY", "")
        
        if not api_key:
            self.logger.warning("OPENAI_API_KEY not configured")
            return
        
        try:
            # Initialize LLM
            self.llm = ChatOpenAI(
                model=self._get_model_name(),
                temperature=0,
                api_key=api_key
            )
            
            # Get tools for this agent
            self.tools = self._get_tools()
            
            if self.tools:
                # Create ReAct agent with LangGraph
                system_prompt = self._get_system_prompt()
                self.agent = create_react_agent(
                    model=self.llm,
                    tools=self.tools,
                    prompt=system_prompt
                )
                self.logger.info(f"Initialized {self.name} with {len(self.tools)} tools")
            else:
                self.logger.warning(f"No tools available for {self.name}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize agent: {e}")
    
    def is_available(self) -> tuple[bool, str]:
        """
        Check if the agent is available to process queries.
        
        Returns:
            Tuple of (is_available, reason_message)
        """
        # Check API key if required
        if self._capabilities.requires_api_key:
            env_var = self._capabilities.api_key_env_var
            if not os.getenv(env_var, ""):
                return False, f"Missing {env_var}"
        
        # Check if agent is initialized
        if self.agent is None:
            return False, "Agent not initialized (check OPENAI_API_KEY)"
        
        return True, "Available"
    
    async def collect(
        self,
        query: str,
        limit: int = 10,
        since: Optional[str] = None
    ) -> List[Any]:  # Returns List[OsintResult] at runtime
        """
        Collect OSINT data for the given query.
        
        This is the main entry point for agent operations.
        
        Args:
            query: The search query or investigation target
            limit: Maximum number of results to return
            since: Optional date filter (ISO format)
            
        Returns:
            List of OsintResult objects
        """
        available, reason = self.is_available()
        if not available:
            self.logger.warning(f"Agent not available: {reason}")
            return []
        
        try:
            # Build the prompt
            prompt = self._build_collection_prompt(query, limit, since)
            
            # Invoke the ReAct agent
            response = await self.agent.ainvoke({
                "messages": [HumanMessage(content=prompt)]
            })
            
            # Parse response into OsintResults
            results = self._parse_agent_response(response)
            
            self.logger.info(f"Collected {len(results)} results for query: {query}")
            return results[:limit]
            
        except Exception as e:
            self.logger.error(f"Collection failed: {e}")
            return []
    
    def _build_collection_prompt(
        self,
        query: str,
        limit: int,
        since: Optional[str]
    ) -> str:
        """Build the collection prompt for the agent."""
        prompt = f"""Investigate the following OSINT query:

Query: {query}

Requirements:
- Find up to {limit} relevant results
- Focus on recent, credible sources
"""
        if since:
            prompt += f"- Only include results from {since} onwards\n"
        
        prompt += """
Please:
1. Use your search tools to find relevant information
2. Extract any indicators of compromise (IOCs) found
3. Summarize your findings
4. Return results as structured JSON

Begin your investigation."""
        
        return prompt
    
    def run(self, query: str, run_id: int = None) -> str:
        """
        Run the agent with a query and return the response as text.
        
        This is a synchronous wrapper around the ReAct agent.
        
        Args:
            query: The query to process
            run_id: Optional run_id for tracing
            
        Returns:
            Agent response as string
        """
        import asyncio
        from agents.tracing import TracingContext, TraceType
        
        available, reason = self.is_available()
        if not available:
            self.logger.warning(f"Agent not available: {reason}")
            return f"Agent not available: {reason}"
        
        # Get tracing context if available
        ctx = TracingContext.get_current()
        trace_id = None
        
        try:
            # Start trace for the agent run
            if ctx:
                trace_id = ctx.start_trace(
                    trace_type=TraceType.AGENT_ACTION.value,
                    agent_name=self.name,
                    instruction=query[:500] if len(query) > 500 else query,
                    input_params={"query": query, "agent": self.name}
                )
            
            # Check if we're already in an async context
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, need to handle differently
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._run_async(query)
                    )
                    result = future.result(timeout=120)
            except RuntimeError:
                # No running loop, we can use asyncio.run
                result = asyncio.run(self._run_async(query))
            
            # Extract evidence from the result for tracing
            evidence = self._extract_evidence_from_result(result)
            confidence = self._calculate_confidence(result, evidence)
            
            # Complete trace with evidence
            if ctx and trace_id:
                ctx.complete_trace(
                    trace_id=trace_id,
                    output=result[:1000] if len(result) > 1000 else result,
                    evidence=evidence,
                    confidence=confidence,
                    reasoning=f"Agent {self.name} completed investigation with {len(evidence)} evidence items"
                )
            
            return result
                
        except Exception as e:
            self.logger.error(f"Run failed: {e}")
            if ctx and trace_id:
                ctx.fail_trace(
                    trace_id=trace_id,
                    error_message=str(e),
                    error_type=type(e).__name__
                )
            return f"Error: {str(e)}"
    
    async def _run_async(self, query: str) -> str:
        """
        Async implementation of run.
        
        Args:
            query: The query to process
            
        Returns:
            Agent response as string
        """
        try:
            response = await self.agent.ainvoke({
                "messages": [HumanMessage(content=query)]
            })
            
            # Extract the final response
            messages = response.get("messages", [])
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    return msg.content
            
            return "No response generated"
            
        except Exception as e:
            self.logger.error(f"Async run failed: {e}")
            return f"Error: {str(e)}"
    
    def _parse_agent_response(self, response: Dict[str, Any]) -> List[Any]:
        """
        Parse agent response into OsintResult objects.
        
        Args:
            response: Raw response from the ReAct agent
            
        Returns:
            List of parsed OsintResult objects
        """
        import json
        OsintResult, ItemType = _get_osint_models()
        results = []
        
        try:
            messages = response.get("messages", [])
            
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    content = msg.content
                    
                    # Try to find JSON in the content
                    json_match = None
                    if "```json" in content:
                        start = content.find("```json") + 7
                        end = content.find("```", start)
                        if end > start:
                            json_match = content[start:end].strip()
                    elif content.strip().startswith("["):
                        json_match = content.strip()
                    
                    if json_match:
                        try:
                            items = json.loads(json_match)
                            if isinstance(items, list):
                                for item in items:
                                    results.append(OsintResult(
                                        title=item.get("title", ""),
                                        url=item.get("url", ""),
                                        summary=item.get("summary", ""),
                                        tags=item.get("tags", []),
                                        indicators=item.get("indicators", []),
                                        source_name=self.name,
                                        published_at=item.get("published_at"),
                                        item_type=ItemType.ARTICLE
                                    ))
                        except json.JSONDecodeError:
                            pass
                    
                    # If no JSON, create a single result from the content
                    if not results and content:
                        results.append(OsintResult(
                            title=f"Analysis: {content[:50]}...",
                            summary=content[:500],
                            url="",
                            source_name=self.name,
                            tags=[],
                            indicators=[],
                            item_type=ItemType.REPORT
                        ))
                    
                    break  # Only process the last AI message
                    
        except Exception as e:
            self.logger.error(f"Failed to parse response: {e}")
        
        return results
    
    def _extract_evidence_from_result(self, result: str) -> List[Dict[str, Any]]:
        """
        Extract evidence (IOCs and entities) from agent result.
        
        Uses regex patterns to find indicators of compromise and
        parses structured JSON evidence if present.
        
        Args:
            result: The agent's response text
            
        Returns:
            List of evidence dictionaries
        """
        import re
        import json
        
        evidence = []
        
        # IOC patterns for extraction
        ioc_patterns = {
            'ip': r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
            'domain': r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:com|net|org|io|gov|edu|info|biz|co|uk|de|ru|cn|jp)\b',
            'url': r'https?://[^\s<>"\'}\]]+',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'md5': r'\b[a-fA-F0-9]{32}\b',
            'sha1': r'\b[a-fA-F0-9]{40}\b',
            'sha256': r'\b[a-fA-F0-9]{64}\b',
            'cve': r'\bCVE-\d{4}-\d{4,7}\b',
            'btc': r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b',
        }
        
        # False positives to skip
        false_positives = {
            'example.com', 'test.com', 'domain.com', 'localhost',
            'google.com', 'github.com', 'twitter.com', 'facebook.com'
        }
        
        seen = set()
        
        # Extract IOCs using patterns
        for ioc_type, pattern in ioc_patterns.items():
            matches = re.findall(pattern, result, re.IGNORECASE)
            for match in matches:
                value = match.lower() if ioc_type != 'cve' else match.upper()
                
                # Skip duplicates and false positives
                key = f"{ioc_type}:{value}"
                if key in seen:
                    continue
                if ioc_type == 'domain' and value in false_positives:
                    continue
                    
                seen.add(key)
                
                # Determine actual type for hashes
                actual_type = ioc_type
                if ioc_type in ('md5', 'sha1', 'sha256'):
                    actual_type = 'hash'
                
                evidence.append({
                    "type": "ioc",
                    "ioc_type": actual_type,
                    "subtype": ioc_type if ioc_type in ('md5', 'sha1', 'sha256') else None,
                    "value": value,
                    "source": self.name
                })
        
        # Try to extract structured evidence from JSON in result
        try:
            if "```json" in result:
                start = result.find("```json") + 7
                end = result.find("```", start)
                if end > start:
                    json_str = result[start:end].strip()
                    data = json.loads(json_str)
                    
                    # Extract IOCs from structured response
                    if isinstance(data, dict):
                        if "evidence" in data and isinstance(data["evidence"], dict):
                            iocs = data["evidence"].get("iocs", [])
                            for ioc in iocs:
                                if isinstance(ioc, dict) and "value" in ioc:
                                    key = f"{ioc.get('type', 'unknown')}:{ioc['value']}"
                                    if key not in seen:
                                        seen.add(key)
                                        evidence.append({
                                            "type": "ioc",
                                            "ioc_type": ioc.get("type", "unknown"),
                                            "value": ioc["value"],
                                            "context": ioc.get("context", ""),
                                            "source": self.name
                                        })
                            
                            # Extract entities
                            entities = data["evidence"].get("entities", [])
                            for entity in entities:
                                if isinstance(entity, dict) and "name" in entity:
                                    evidence.append({
                                        "type": "entity",
                                        "entity_type": entity.get("type", "unknown"),
                                        "name": entity["name"],
                                        "context": entity.get("context", ""),
                                        "source": self.name
                                    })
                            
                            # Extract MITRE ATT&CK techniques
                            techniques = data["evidence"].get("techniques", [])
                            for technique in techniques:
                                if technique:
                                    evidence.append({
                                        "type": "technique",
                                        "mitre_id": technique,
                                        "source": self.name
                                    })
                        
                        # Also check top-level findings
                        if "findings" in data and isinstance(data["findings"], list):
                            for finding in data["findings"]:
                                if isinstance(finding, dict) and finding.get("source_url"):
                                    url = finding["source_url"]
                                    key = f"source_url:{url}"
                                    if key not in seen:
                                        seen.add(key)
                                        evidence.append({
                                            "type": "source",
                                            "url": url,
                                            "title": finding.get("title", ""),
                                            "confidence": finding.get("confidence", 0.5),
                                            "source": self.name
                                        })
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.debug(f"Could not parse structured evidence: {e}")
        
        return evidence
    
    def _calculate_confidence(self, result: str, evidence: List[Dict]) -> float:
        """
        Calculate confidence score based on result quality and evidence.
        
        Args:
            result: The agent's response text
            evidence: Extracted evidence list
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        import json
        
        confidence = 0.3  # Base confidence
        
        # Boost for having evidence
        if evidence:
            confidence += min(0.3, len(evidence) * 0.05)
        
        # Try to get confidence from structured response
        try:
            if "```json" in result:
                start = result.find("```json") + 7
                end = result.find("```", start)
                if end > start:
                    data = json.loads(result[start:end].strip())
                    if isinstance(data, dict) and "confidence_score" in data:
                        # Ensure returned confidence is valid (0.0-1.0)
                        reported_confidence = float(data["confidence_score"])
                        return max(0.0, min(1.0, reported_confidence))
        except:
            pass
        
        # Boost for having sources
        sources_found = result.lower().count("http")
        confidence += min(0.2, sources_found * 0.03)
        
        # Boost for structured output
        if "```json" in result:
            confidence += 0.1
        
        return min(1.0, confidence)
