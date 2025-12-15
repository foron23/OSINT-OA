# =============================================================================
# OSINT News Aggregator - Agents Package
# =============================================================================
"""
Agents package for OSINT collection and orchestration.

All agents use LangGraph with ReAct pattern for intelligent OSINT gathering.

Modules:
- base: Base agent classes and capabilities
- registry: Agent discovery and registration
- control: Investigation orchestration
- consolidator: Report publishing to Telegram
- langgraph_core: Advanced LangGraph state management
- osint/: OSINT-specialized agents

Usage:
    from agents import AgentRegistry, ControlAgent
    
    # Get an agent
    agent = AgentRegistry.get("TavilySearchAgent")
    result = agent.run("Search for latest cybersecurity threats")
    
    # Or use control agent for orchestrated investigations
    control = ControlAgent()
    report = control.investigate("APT29 recent activity")
    
    # Use LangGraph for advanced workflows
    from agents.langgraph_core import create_investigation_graph
    graph = create_investigation_graph(tools, human_review=True)
"""

# Base classes
from agents.base import LangChainAgent, AgentCapabilities

# Registry
from agents.registry import (
    AgentRegistry,
    get_agent,
    list_agents,
    register_all_agents,
    # Backward compatibility
    LangChainAgentRegistry,
)

# Control agents
from agents.control import ControlAgent
from agents.consolidator import ConsolidatorAgent

# LangGraph advanced features
from agents.langgraph_core import (
    LangGraphAgentBuilder,
    InvestigationState,
    InvestigationPhase,
    SimpleAgentState,
    create_simple_react_agent,
    create_investigation_graph,
    run_investigation,
)

# Tracing module for execution traceability
from agents.tracing import (
    TracingContext,
    traced,
    trace_investigation,
    record_tool_call,
    record_agent_action,
)

# OSINT agents
from agents.osint import (
    # Search agents
    TavilySearchAgent,
    DuckDuckGoSearchAgent,
    GoogleDorkingAgent,
    # Analysis agents
    WebScraperAgent,
    ThreatIntelAgent,
    IOCAnalysisAgent,
    # Hybrid agent
    HybridOsintAgent,
    # Report agent
    ReportGeneratorAgent,
    # Modern OSINT agents
    MaigretAgent,
    BbotAgent,
)

# Backward compatibility aliases
LangChainOsintAgent = LangChainAgent
LangChainAgentCapabilities = AgentCapabilities
TavilySearchOsintAgent = TavilySearchAgent
DuckDuckGoSearchOsintAgent = DuckDuckGoSearchAgent
GoogleDorkingOsintAgent = GoogleDorkingAgent
WebScraperOsintAgent = WebScraperAgent
ThreatIntelOsintAgent = ThreatIntelAgent
StandardWebSearchOsintAgent = DuckDuckGoSearchAgent


def init_agents() -> None:
    """Initialize and register all agents."""
    register_all_agents()


__all__ = [
    # Base
    "LangChainAgent",
    "AgentCapabilities",
    # Registry
    "AgentRegistry",
    "LangChainAgentRegistry",
    "get_agent",
    "list_agents",
    "register_all_agents",
    "init_agents",
    # Control agents
    "ControlAgent",
    "ConsolidatorAgent",
    # LangGraph advanced features
    "LangGraphAgentBuilder",
    "InvestigationState",
    "InvestigationPhase",
    "SimpleAgentState",
    "create_simple_react_agent",
    "create_investigation_graph",
    "run_investigation",
    # Tracing
    "TracingContext",
    "traced",
    "trace_investigation",
    "record_tool_call",
    "record_agent_action",
    # OSINT agents
    "TavilySearchAgent",
    "DuckDuckGoSearchAgent",
    "GoogleDorkingAgent",
    "WebScraperAgent",
    "ThreatIntelAgent",
    "IOCAnalysisAgent",
    "HybridOsintAgent",
    "ReportGeneratorAgent",
    "MaigretAgent",
    "BbotAgent",
    # Backward compatibility
    "LangChainOsintAgent",
    "LangChainAgentCapabilities",
    "TavilySearchOsintAgent",
    "DuckDuckGoSearchOsintAgent",
    "GoogleDorkingOsintAgent",
    "WebScraperOsintAgent",
    "ThreatIntelOsintAgent",
    "StandardWebSearchOsintAgent",
]
