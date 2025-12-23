# =============================================================================
# Control Agent - Investigation Orchestrator
# =============================================================================
"""
Control agent for orchestrating OSINT agentic operations.

Provides:
- ControlAgent: Plans and coordinates multi-agent investigations
- Evidence feedback loop: Shares IOCs between agents for deeper analysis
"""

import logging
import json
import signal
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from concurrent.futures import TimeoutError as FuturesTimeoutError

from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI

from agents.base import LangChainAgent, AgentCapabilities
from agents.registry import AgentRegistry
from agents.tracing import TracingContext, TraceType
from agents.evidence_store import (
    EvidenceStore, IOC, Finding, IOCType, 
    get_evidence_context, AGENT_TYPE_MAP
)


# =============================================================================
# Investigation Result Tracking
# =============================================================================

@dataclass
class AgentResult:
    """Result from a single agent delegation."""
    agent_name: str
    success: bool
    result: str = ""
    error: str = ""
    duration_seconds: float = 0.0
    iocs_extracted: int = 0


@dataclass
class InvestigationProgress:
    """Track partial progress during investigation."""
    run_id: Optional[int] = None
    topic: str = ""
    depth: str = "standard"
    started_at: Optional[datetime] = None
    agent_results: List[AgentResult] = field(default_factory=list)
    partial_findings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_iocs: int = 0
    
    def add_agent_result(self, result: AgentResult):
        """Add an agent result to progress tracking."""
        self.agent_results.append(result)
        if result.success:
            self.total_iocs += result.iocs_extracted
        else:
            self.errors.append(f"{result.agent_name}: {result.error}")
    
    def has_useful_results(self) -> bool:
        """Check if we have enough results for a partial report."""
        successful = sum(1 for r in self.agent_results if r.success)
        return successful >= 1
    
    def get_successful_count(self) -> int:
        """Count successful agent delegations."""
        return sum(1 for r in self.agent_results if r.success)
    
    def get_failed_count(self) -> int:
        """Count failed agent delegations."""
        return sum(1 for r in self.agent_results if not r.success)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert progress to dictionary."""
        return {
            "run_id": self.run_id,
            "topic": self.topic,
            "depth": self.depth,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "agents_succeeded": self.get_successful_count(),
            "agents_failed": self.get_failed_count(),
            "errors": self.errors,
            "total_iocs": self.total_iocs,
            "has_useful_results": self.has_useful_results(),
        }


# Thread-local storage for investigation progress
_investigation_progress = threading.local()

logger = logging.getLogger(__name__)

# Agent timeout configuration (seconds)
AGENT_TIMEOUT_QUICK = 30
AGENT_TIMEOUT_STANDARD = 60
AGENT_TIMEOUT_DEEP = 120

def get_agent_timeout(depth: str = "standard") -> int:
    """Get timeout based on investigation depth."""
    return {
        "quick": AGENT_TIMEOUT_QUICK,
        "standard": AGENT_TIMEOUT_STANDARD,
        "deep": AGENT_TIMEOUT_DEEP,
    }.get(depth, AGENT_TIMEOUT_STANDARD)


def get_investigation_progress() -> Optional[InvestigationProgress]:
    """Get current investigation progress."""
    return getattr(_investigation_progress, 'progress', None)


def set_investigation_progress(progress: Optional[InvestigationProgress]):
    """Set current investigation progress."""
    _investigation_progress.progress = progress


# Thread-local storage for current run context
import threading
_current_run_context = threading.local()


def set_current_run_id(run_id: int):
    """Set the current run_id for evidence tracking."""
    _current_run_context.run_id = run_id


def get_current_run_id() -> Optional[int]:
    """Get the current run_id."""
    return getattr(_current_run_context, 'run_id', None)


@tool
def delegate_to_agent(agent_name: str, query: str) -> str:
    """
    Delegate a query to a specific OSINT agent.
    
    Automatically includes evidence feedback from other agents
    when a run_id is set, enabling cross-agent intelligence sharing.
    Tracks results for partial completion support.
    
    Args:
        agent_name: Name of the agent to delegate to
        query: The query to execute
        
    Returns:
        Agent response or error message
    """
    start_time = datetime.now()
    progress = get_investigation_progress()
    
    try:
        agent = AgentRegistry.get(agent_name)
        if not agent:
            available = AgentRegistry.list_all()
            error_msg = f"Agent '{agent_name}' not found. Available: {', '.join(available)}"
            if progress:
                progress.add_agent_result(AgentResult(
                    agent_name=agent_name,
                    success=False,
                    error=error_msg,
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                ))
            return error_msg
        
        available, reason = agent.is_available()
        if not available:
            error_msg = f"Agent '{agent_name}' is not available: {reason}"
            if progress:
                progress.add_agent_result(AgentResult(
                    agent_name=agent_name,
                    success=False,
                    error=error_msg,
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                ))
            return error_msg
        
        # Get current run_id for evidence tracking
        run_id = get_current_run_id()
        
        # Build enhanced query with evidence feedback
        enhanced_query = query
        if run_id:
            evidence_ctx = get_evidence_context(run_id, agent_name)
            if evidence_ctx.get("feedback_prompt"):
                enhanced_query = f"{query}\n\n{evidence_ctx['feedback_prompt']}"
                logger.info(f"Added evidence feedback to {agent_name} query (run #{run_id})")
        
        # Run the agent with enhanced query
        result = agent.run(enhanced_query, run_id=run_id)
        
        # Extract and store evidence from result
        iocs_count = 0
        if run_id:
            store = EvidenceStore.get_or_create(run_id)
            # Extract IOCs from the result text
            iocs = store.add_iocs_from_text(result, agent_name, f"Query: {query[:100]}")
            iocs_count = len(iocs) if iocs else 0
            if iocs:
                logger.info(f"Agent {agent_name} contributed {len(iocs)} IOCs to evidence store")
        
        # Track successful result
        if progress:
            progress.add_agent_result(AgentResult(
                agent_name=agent_name,
                success=True,
                result=result[:500] if result else "",  # Truncate for tracking
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                iocs_extracted=iocs_count
            ))
        
        return result
        
    except Exception as e:
        error_msg = f"Error delegating to {agent_name}: {str(e)}"
        logger.error(f"Delegation to {agent_name} failed: {e}")
        
        # Track failed result for partial completion
        if progress:
            progress.add_agent_result(AgentResult(
                agent_name=agent_name,
                success=False,
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds()
            ))
        
        return error_msg


@tool
def delegate_with_evidence_feedback(agent_name: str, query: str, include_iocs: bool = True) -> str:
    """
    Delegate a query to an agent with explicit evidence from other agents.
    
    This tool ensures the agent receives IOCs discovered by other agents
    during the same investigation, enabling deeper analysis.
    
    Args:
        agent_name: Name of the agent to delegate to
        query: The query to execute
        include_iocs: Whether to include IOCs from other agents
        
    Returns:
        Agent response with evidence collection
    """
    try:
        agent = AgentRegistry.get(agent_name)
        if not agent:
            available = AgentRegistry.list_all()
            return f"Agent '{agent_name}' not found. Available: {', '.join(available)}"
        
        available, reason = agent.is_available()
        if not available:
            return f"Agent '{agent_name}' is not available: {reason}"
        
        run_id = get_current_run_id()
        
        # Build query with evidence
        enhanced_query = query
        if run_id and include_iocs:
            evidence_ctx = get_evidence_context(run_id, agent_name)
            
            if evidence_ctx.get("relevant_iocs"):
                ioc_list = evidence_ctx["relevant_iocs"]
                ioc_summary = "\n".join([
                    f"  - [{ioc['type']}] {ioc['value']}" 
                    for ioc in ioc_list[:15]
                ])
                enhanced_query = f"""{query}

=== CROSS-AGENT INTELLIGENCE ===
The following IOCs were discovered by other agents in this investigation.
Incorporate them into your analysis where relevant:

{ioc_summary}

Use these to find additional connections and deepen the investigation.
=================================
"""
        
        # Run agent
        result = agent.run(enhanced_query, run_id=run_id)
        
        # Store evidence
        if run_id:
            store = EvidenceStore.get_or_create(run_id)
            store.add_iocs_from_text(result, agent_name, f"Query: {query[:100]}")
        
        return result
        
    except Exception as e:
        logger.error(f"Delegation with feedback to {agent_name} failed: {e}")
        return f"Error: {str(e)}"


@tool
def get_shared_evidence_summary() -> str:
    """
    Get a summary of all evidence collected so far in this investigation.
    
    Returns a summary of IOCs, findings, and statistics from all agents.
    
    Returns:
        Evidence summary or message if no evidence available
    """
    run_id = get_current_run_id()
    if not run_id:
        # Return a clear message that won't cause retry loops
        return """Evidence Summary: No IOCs tracked yet.
        
This is normal for quick investigations or early in the process.
Continue with your investigation - evidence will accumulate as agents report findings.
Proceed to synthesize findings from agent responses directly."""
    
    store = EvidenceStore.get(run_id)
    if not store:
        return """Evidence Summary: Collection initialized but empty.
        
No IOCs have been extracted from agent responses yet.
This may happen if agents found general information without specific indicators.
Proceed to synthesize your findings from the agent responses."""
    
    return store.get_investigation_summary()


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
            description="Orchestrates OSINT investigations across multiple agents with evidence sharing",
            tools=[
                "delegate_to_agent", 
                "delegate_with_evidence_feedback",
                "get_shared_evidence_summary",
                "list_available_agents", 
                "get_agent_info"
            ],
            supported_queries=["investigate", "research", "analyze", "comprehensive"],
        )
    
    def _get_tools(self) -> List[BaseTool]:
        """Get control/orchestration tools with evidence feedback support."""
        return [
            delegate_to_agent,
            delegate_with_evidence_feedback,
            get_shared_evidence_summary,
            list_available_agents,
            get_agent_info,
        ]
    
    def _get_system_prompt(self) -> str:
        return """You are the CONTROL AGENT - the orchestrator of a collaborative OSINT Agentic Operations system.

=== YOUR MISSION ===
Coordinate multi-agent investigations to gather comprehensive intelligence. Delegate tasks to specialized agents, synthesize their findings, and produce actionable reports.

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

**Identity & Contact OSINT:**
- **MaigretAgent**: Username OSINT across 500+ platforms
- **HoleheAgent**: Email registration check across 100+ sites
- **PhoneInfogaAgent**: Phone number intelligence (carrier, country, footprint)

**Infrastructure OSINT:**
- **BbotAgent**: Attack surface enumeration and domain reconnaissance

=== INVESTIGATION WORKFLOW ===

**Phase 1: PLANNING**
1. Analyze the investigation request
2. Select appropriate agents based on the objective

**Phase 2: COLLECTION**
3. Delegate to search agents (TavilySearch, DuckDuckGo)
4. Look for IOCs in their responses (IPs, domains, emails, usernames, phones)

**Phase 3: DEEP DIVE (for standard/deep investigations)**
5. Use delegate_with_evidence_feedback to share discovered IOCs with specialized agents
6. MaigretAgent for usernames discovered
7. HoleheAgent for emails discovered
8. PhoneInfogaAgent for phone numbers discovered
9. BbotAgent for domains/IPs discovered

**Phase 4: SYNTHESIS**
10. Synthesize and cross-reference findings from all agents
11. Identify patterns and relationships
12. Produce comprehensive report

=== DELEGATION BEST PRACTICES ===
- **First pass**: TavilySearchAgent + DuckDuckGoSearchAgent
- **Username discovered**: delegate_with_evidence_feedback to MaigretAgent
- **Email discovered**: delegate_with_evidence_feedback to HoleheAgent
- **Phone discovered**: delegate_with_evidence_feedback to PhoneInfogaAgent
- **Domain discovered**: delegate_with_evidence_feedback to BbotAgent
- **Threat actor research**: ThreatIntelAgent + IOCAnalysisAgent

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
[Which agents were used and evidence flow between them]

### Evidence Collection Statistics
[Total IOCs, cross-references, agents contributing]

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
- For deep investigations, do multiple passes sharing IOCs between agents
- Synthesize, don't just concatenate findings
- Highlight conflicts or gaps in intelligence
- Provide actionable recommendations"""
    
    def investigate(
        self,
        topic: str,
        agents: Optional[List[str]] = None,
        depth: str = "standard",
        run_id: Optional[int] = None,
        continue_from: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Conduct a full investigation on a topic.
        
        Uses the EvidenceStore for cross-agent intelligence sharing
        when run_id is provided. Supports partial completion on errors.
        
        Args:
            topic: The topic to investigate
            agents: Specific agents to use (optional)
            depth: Investigation depth (quick/standard/deep)
            run_id: Optional run_id for tracing and evidence tracking
            continue_from: Optional context from a previous investigation to continue
            
        Returns:
            Investigation results with evidence summary
        """
        start_time = datetime.now()
        evidence_store = None
        status = "completed"  # Will change to "partial" if errors occur
        
        # Initialize progress tracking for partial completion
        progress = InvestigationProgress(
            run_id=run_id,
            topic=topic,
            depth=depth,
            started_at=start_time
        )
        set_investigation_progress(progress)
        
        # Initialize evidence store and run context for this investigation
        if run_id:
            evidence_store = EvidenceStore.get_or_create(run_id)
            set_current_run_id(run_id)
            logger.info(f"Initialized EvidenceStore for run #{run_id}")
        
        # Create tracing context if run_id provided
        tracing_ctx = None
        if run_id:
            tracing_ctx = TracingContext(run_id=run_id, agent_name="ControlAgent")
        
        result = ""
        partial_result = False
        
        try:
            if tracing_ctx:
                tracing_ctx.__enter__()
                # Record investigation start
                tracing_ctx.add_decision(
                    decision=f"Starting {depth} investigation on: {topic}",
                    reasoning=f"User requested investigation with depth={depth}, agents={agents or 'auto-select'}",
                    options_considered=["quick", "standard", "deep"]
                )
        
            # Build investigation query with depth-specific instructions
            if agents:
                agent_hint = f"Use these agents: {', '.join(agents)}"
            else:
                agent_hint = "Select appropriate agents from the registry"
            
            depth_instructions = {
                "quick": """Conduct a quick investigation:
- Use 1-2 agents for key findings only
- Single pass, synthesize directly from responses""",
                "standard": """Standard investigation:
- Use 2-4 agents for balanced depth
- Delegate to agents and synthesize their responses
- Look for IOCs (IPs, domains, emails) in responses""",
                "deep": """Deep investigation - MULTI-PASS REQUIRED:
- Use all relevant agents with comprehensive analysis
- After first round of delegations, look for IOCs in responses
- Use delegate_with_evidence_feedback to share discovered IOCs with specialized agents
- Minimum 2 passes required for deep investigations"""
            }
            
            # Handle continuation from previous investigation
            context_hint = ""
            if continue_from:
                prev_findings = continue_from.get("previous_findings", "")
                prev_iocs = continue_from.get("previous_iocs", [])
                new_instructions = continue_from.get("new_instructions", "")
                selected_evidence = continue_from.get("selected_evidence", [])
                
                context_hint = f"""
=== CONTINUING PREVIOUS INVESTIGATION ===
Previous findings summary:
{prev_findings[:2000] if prev_findings else 'None available'}

{"Previous IOCs to investigate further: " + ', '.join(prev_iocs[:20]) if prev_iocs else ''}
{"Focus on these evidence items: " + ', '.join(selected_evidence[:10]) if selected_evidence else ''}
New instructions: {new_instructions or 'Continue investigation with deeper analysis'}
==========================================
"""
            
            query = f"""
Investigate: {topic}

Depth: {depth_instructions.get(depth, depth_instructions["standard"])}
{agent_hint}
{context_hint}

Instructions:
1. Delegate to appropriate search agents
2. Analyze their responses for IOCs (IPs, domains, emails, usernames)
3. For standard/deep: use delegate_with_evidence_feedback to share IOCs with specialized agents
4. Synthesize all findings into a comprehensive report

Provide a comprehensive investigation report.
"""
            
            if tracing_ctx:
                tracing_ctx.add_reasoning(
                    reasoning=f"Constructed investigation query with depth={depth}, evidence feedback enabled",
                    context={"query_length": len(query), "topic": topic, "run_id": run_id}
                )
            
            # Run investigation with error handling for partial completion
            try:
                result = self.run(query, run_id=run_id)
            except Exception as e:
                logger.error(f"Investigation agent error: {e}")
                progress.errors.append(f"ControlAgent: {str(e)}")
                
                # Try to generate partial report from collected results
                if progress.has_useful_results():
                    partial_result = True
                    status = "partial"
                    result = self._generate_partial_report(topic, progress, evidence_store)
                    logger.info(f"Generated partial report for run #{run_id} with {progress.get_successful_count()} agent results")
                else:
                    # Re-raise if we have nothing useful
                    raise
            
            # Check if we had agent errors but main loop completed
            if progress.get_failed_count() > 0 and not partial_result:
                status = "partial"
                logger.warning(f"Investigation #{run_id} completed with {progress.get_failed_count()} agent errors")
            
            # Get evidence summary if store is available
            evidence_summary = None
            evidence_summary_text = None
            if evidence_store:
                evidence_summary = evidence_store.get_stats().to_dict()
                evidence_summary_text = evidence_store.get_investigation_summary()
                logger.info(f"Investigation #{run_id} collected {evidence_summary['total_iocs']} IOCs")
            
            if tracing_ctx:
                tracing_ctx.add_checkpoint(
                    name="investigation_complete",
                    state={
                        "topic": topic,
                        "depth": depth,
                        "result_length": len(result) if result else 0,
                        "evidence_stats": evidence_summary,
                        "status": status,
                        "partial": partial_result,
                        "agent_errors": progress.get_failed_count()
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
                "evidence_summary": evidence_summary,
                "status": status,
            }
            self._investigation_history.append(investigation)
            
            return {
                "success": True,
                "partial": partial_result,
                "status": status,
                "topic": topic,
                "report": result,
                "evidence": {
                    "summary": evidence_summary_text,
                    "stats": evidence_summary,
                } if evidence_summary else None,
                "progress": progress.to_dict(),
                "metadata": {
                    "timestamp": start_time.isoformat(),
                    "depth": depth,
                    "agents_used": agents or "auto-selected",
                    "duration_seconds": (datetime.now() - start_time).total_seconds(),
                    "run_id": run_id,
                    "agents_succeeded": progress.get_successful_count(),
                    "agents_failed": progress.get_failed_count(),
                }
            }
        except Exception as e:
            # Even on error, try to return what we have
            logger.error(f"Investigation failed: {e}")
            
            if progress.has_useful_results():
                # Generate partial report from what we have
                try:
                    partial_report = self._generate_partial_report(topic, progress, evidence_store)
                    return {
                        "success": False,
                        "partial": True,
                        "status": "partial",
                        "topic": topic,
                        "report": partial_report,
                        "error": str(e),
                        "progress": progress.to_dict(),
                        "metadata": {
                            "timestamp": start_time.isoformat(),
                            "depth": depth,
                            "agents_used": agents or "auto-selected",
                            "duration_seconds": (datetime.now() - start_time).total_seconds(),
                            "run_id": run_id,
                            "agents_succeeded": progress.get_successful_count(),
                            "agents_failed": progress.get_failed_count(),
                        }
                    }
                except Exception as partial_error:
                    logger.error(f"Failed to generate partial report: {partial_error}")
            
            # Complete failure
            return {
                "success": False,
                "partial": False,
                "status": "failed",
                "topic": topic,
                "report": f"Investigation failed: {str(e)}",
                "error": str(e),
                "progress": progress.to_dict(),
                "metadata": {
                    "timestamp": start_time.isoformat(),
                    "depth": depth,
                    "duration_seconds": (datetime.now() - start_time).total_seconds(),
                    "run_id": run_id,
                }
            }
        finally:
            # Clean up run context
            set_investigation_progress(None)
            if run_id:
                set_current_run_id(None)
                # Note: We don't cleanup EvidenceStore here as it might be needed for reporting
            if tracing_ctx:
                tracing_ctx.__exit__(None, None, None)
    
    def _generate_partial_report(
        self, 
        topic: str, 
        progress: InvestigationProgress, 
        evidence_store: Optional[EvidenceStore]
    ) -> str:
        """
        Generate a partial report from collected agent results.
        
        Called when the main investigation loop fails but we have
        some useful results from agents.
        """
        sections = [
            f"## Partial Investigation Report\n",
            f"**Topic:** {topic}\n",
            f"**Status:** Partial completion due to errors\n",
            f"**Agents Succeeded:** {progress.get_successful_count()}\n",
            f"**Agents Failed:** {progress.get_failed_count()}\n",
        ]
        
        if progress.errors:
            sections.append("\n### Errors Encountered\n")
            for error in progress.errors[:10]:  # Limit to first 10
                sections.append(f"- {error}\n")
        
        # Add successful agent findings
        sections.append("\n### Collected Findings\n")
        for result in progress.agent_results:
            if result.success and result.result:
                sections.append(f"\n#### From {result.agent_name}\n")
                sections.append(f"{result.result}\n")
        
        # Add evidence summary if available
        if evidence_store:
            sections.append("\n### Evidence Summary\n")
            sections.append(evidence_store.get_investigation_summary() or "No IOCs extracted.\n")
        
        sections.append("\n### Recommendations\n")
        sections.append("- Review the errors above and retry failed agents individually\n")
        sections.append("- Consider using a lower depth setting for more stable results\n")
        sections.append("- Use the 'Continue Investigation' feature to resume with specific agents\n")
        
        return "".join(sections)
    
    @property
    def investigation_history(self) -> List[Dict[str, Any]]:
        """Get the investigation history."""
        return self._investigation_history.copy()
