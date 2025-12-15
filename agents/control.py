# =============================================================================
# Control Agent - Investigation Orchestrator
# =============================================================================
"""
Control agent for orchestrating OSINT agentic operations.

Provides:
- ControlAgent: Plans and coordinates multi-agent investigations
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI

from agents.base import LangChainAgent, AgentCapabilities
from agents.registry import AgentRegistry
from agents.tracing import TracingContext, TraceType

logger = logging.getLogger(__name__)


@tool
def delegate_to_agent(agent_name: str, query: str) -> str:
    """
    Delegate a query to a specific OSINT agent.
    
    Args:
        agent_name: Name of the agent to delegate to
        query: The query to execute
        
    Returns:
        Agent response or error message
    """
    try:
        agent = AgentRegistry.get(agent_name)
        if not agent:
            available = AgentRegistry.list_all()
            return f"Agent '{agent_name}' not found. Available: {', '.join(available)}"
        
        available, reason = agent.is_available()
        if not available:
            return f"Agent '{agent_name}' is not available: {reason}"
        
        result = agent.run(query)
        return result
        
    except Exception as e:
        logger.error(f"Delegation to {agent_name} failed: {e}")
        return f"Error delegating to {agent_name}: {str(e)}"


@tool
def list_available_agents() -> str:
    """
    List all available OSINT agents and their capabilities.
    
    Returns:
        JSON string of available agents
    """
    agents = AgentRegistry.list_available()
    return json.dumps(agents, indent=2)


@tool
def get_agent_info(agent_name: str) -> str:
    """
    Get detailed information about a specific agent.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        Agent details or error message
    """
    agent = AgentRegistry.get(agent_name)
    if not agent:
        return f"Agent '{agent_name}' not found"
    
    caps = agent.capabilities
    available, reason = agent.is_available()
    
    return json.dumps({
        "name": caps.name,
        "description": caps.description,
        "tools": caps.tools,
        "supported_queries": caps.supported_queries,
        "available": available,
        "availability_reason": reason,
    }, indent=2)


class ControlAgent(LangChainAgent):
    """
    Control agent that orchestrates multi-agent investigations.
    
    Plans investigation strategies, delegates to specialized agents,
    and synthesizes results into cohesive reports.
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        Initialize the control agent.
        
        Args:
            model_name: OpenAI model to use
        """
        self._model_name = model_name
        super().__init__()
        self._investigation_history: List[Dict[str, Any]] = []
    
    def _define_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(
            name="ControlAgent",
            description="Orchestrates OSINT investigations across multiple agents",
            tools=["delegate_to_agent", "list_available_agents", "get_agent_info"],
            supported_queries=["investigate", "research", "analyze", "comprehensive"],
        )
    
    def _get_tools(self) -> List[BaseTool]:
        """Get control/orchestration tools."""
        return [
            delegate_to_agent,
            list_available_agents,
            get_agent_info,
        ]
    
    def _get_system_prompt(self) -> str:
        return """You are the CONTROL AGENT - the orchestrator of a collaborative OSINT Agentic Operations system.

=== YOUR MISSION ===
Coordinate multi-agent investigations to gather comprehensive intelligence. You plan strategies, delegate tasks to specialized agents, synthesize their findings, and produce actionable intelligence reports.

=== AVAILABLE AGENTS ===
**Search Specialists:**
- **TavilySearchAgent**: AI-optimized web search for broad intelligence
- **DuckDuckGoSearchAgent**: Privacy-focused search for diverse sources
- **GoogleDorkingAgent**: Advanced search techniques for hidden data

**Analysis Specialists:**
- **WebScraperAgent**: Deep content extraction from web pages
- **ThreatIntelAgent**: Threat intelligence, APTs, and vulnerability analysis
- **IOCAnalysisAgent**: Indicator of Compromise extraction and enrichment
- **HybridOsintAgent**: Multi-tool comprehensive analysis

**Specialized Tools:**
- **MaigretAgent**: Username OSINT across 500+ platforms
- **BbotAgent**: Attack surface enumeration and domain reconnaissance

=== INVESTIGATION WORKFLOW ===

**Phase 1: PLANNING**
1. Analyze the investigation request
2. List available agents using list_available_agents
3. Select appropriate agents based on the objective

**Phase 2: EXECUTION**
4. Delegate specific queries to each selected agent
5. Request agents to extract IOCs and evidence
6. Gather responses from all agents

**Phase 3: SYNTHESIS**
7. Combine findings from all agents
8. Cross-reference and validate evidence
9. Identify patterns and relationships
10. Produce comprehensive report

=== DELEGATION BEST PRACTICES ===
- **Threat investigations**: Use ThreatIntelAgent + IOCAnalysisAgent + TavilySearchAgent
- **Person/username research**: Use MaigretAgent + DuckDuckGoSearchAgent
- **Domain reconnaissance**: Use BbotAgent + GoogleDorkingAgent
- **General research**: Use HybridOsintAgent for comprehensive coverage
- **Deep analysis**: Combine search agents with WebScraperAgent

=== EVIDENCE REQUIREMENTS ===
Ensure ALL delegated agents collect and return:
- IOCs: IP addresses, domains, URLs, hashes, emails, CVEs
- Entities: People, organizations, threat actors, malware names
- Techniques: MITRE ATT&CK IDs when applicable
- Sources: URLs for every finding
- Confidence scores for each piece of evidence

=== OUTPUT FORMAT ===

## Investigation Report

### Executive Summary
[2-3 sentence overview of key findings]

### Request Analysis
[What was asked and investigation approach taken]

### Agent Deployment
[Which agents were used and why]

### Key Findings
[Synthesized results with evidence]

#### Indicators of Compromise
| Type | Value | Context | Confidence |
|------|-------|---------|------------|
| ip | x.x.x.x | Found in... | 0.9 |

#### Entities Identified
[Threat actors, organizations, people, software]

#### MITRE ATT&CK Mapping
[Techniques if applicable]

### Assessment
[Analysis, conclusions, threat level]

### Recommendations
[Actionable next steps]

### Sources
[All source URLs with attribution]

### Confidence Score
[Overall confidence: 0.0-1.0]

=== QUALITY STANDARDS ===
- Always delegate to 2+ agents for cross-verification
- Request structured JSON evidence from agents
- Synthesize, don't just concatenate findings
- Highlight conflicts or gaps in intelligence
- Provide actionable recommendations"""
    
    def investigate(
        self,
        topic: str,
        agents: Optional[List[str]] = None,
        depth: str = "standard",
        run_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Conduct a full investigation on a topic.
        
        Args:
            topic: The topic to investigate
            agents: Specific agents to use (optional)
            depth: Investigation depth (quick/standard/deep)
            run_id: Optional run_id for tracing
            
        Returns:
            Investigation results
        """
        start_time = datetime.now()
        
        # Create tracing context if run_id provided
        tracing_ctx = None
        if run_id:
            tracing_ctx = TracingContext(run_id=run_id, agent_name="ControlAgent")
        
        try:
            if tracing_ctx:
                tracing_ctx.__enter__()
                # Record investigation start
                tracing_ctx.add_decision(
                    decision=f"Starting {depth} investigation on: {topic}",
                    reasoning=f"User requested investigation with depth={depth}, agents={agents or 'auto-select'}",
                    options_considered=["quick", "standard", "deep"]
                )
        
            # Build investigation query
            if agents:
                agent_hint = f"Use these agents: {', '.join(agents)}"
            else:
                agent_hint = "Select appropriate agents from the registry"
            
            depth_instructions = {
                "quick": "Conduct a quick investigation - 1-2 agents, key findings only",
                "standard": "Standard investigation - 2-4 agents, balanced depth",
                "deep": "Deep investigation - use all relevant agents, comprehensive analysis"
            }
            
            query = f"""
Investigate: {topic}

Depth: {depth_instructions.get(depth, depth_instructions["standard"])}
{agent_hint}

Provide a comprehensive investigation report.
"""
            
            if tracing_ctx:
                tracing_ctx.add_reasoning(
                    reasoning=f"Constructed investigation query with depth={depth}",
                    context={"query_length": len(query), "topic": topic}
                )
            
            # Run investigation
            result = self.run(query, run_id=run_id)
            
            if tracing_ctx:
                tracing_ctx.add_checkpoint(
                    name="investigation_complete",
                    state={
                        "topic": topic,
                        "depth": depth,
                        "result_length": len(result) if result else 0
                    }
                )
            
            # Record in history
            investigation = {
                "topic": topic,
                "timestamp": start_time.isoformat(),
                "duration": (datetime.now() - start_time).total_seconds(),
                "agents": agents,
                "depth": depth,
                "result": result[:500] + "..." if len(result) > 500 else result,
            }
            self._investigation_history.append(investigation)
            
            return {
                "success": True,
                "topic": topic,
                "report": result,
                "metadata": {
                    "timestamp": start_time.isoformat(),
                    "depth": depth,
                    "agents_used": agents or "auto-selected",
                    "duration_seconds": (datetime.now() - start_time).total_seconds()
                }
            }
        finally:
            if tracing_ctx:
                tracing_ctx.__exit__(None, None, None)
    
    @property
    def investigation_history(self) -> List[Dict[str, Any]]:
        """Get the investigation history."""
        return self._investigation_history.copy()
