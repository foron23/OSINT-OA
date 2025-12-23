# =============================================================================
# OSINT OA - LangGraph Core
# =============================================================================
"""
LangGraph integration module for advanced agent orchestration.

This module provides:
- State definitions for OSINT investigation workflows
- Graph builders for different investigation patterns
- Human-in-the-loop checkpoints for sensitive operations
- Observability with LangSmith tracing

Architecture:
- Uses StateGraph for typed state management
- Implements checkpoints for state persistence
- Supports human review before sensitive actions
"""

import os
import logging
from typing import TypedDict, List, Dict, Any, Optional, Annotated, Literal, Sequence, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from pydantic import SecretStr

logger = logging.getLogger(__name__)

# Type alias for compiled graphs (avoid strict type checking issues)
CompiledGraph = Any


# =============================================================================
# State Definitions
# =============================================================================

class InvestigationPhase(str, Enum):
    """Phases of an OSINT investigation."""
    PLANNING = "planning"
    COLLECTION = "collection"
    ANALYSIS = "analysis"
    VERIFICATION = "verification"
    REPORTING = "reporting"
    COMPLETE = "complete"


class InvestigationState(TypedDict):
    """
    State for OSINT investigation graph.
    
    Tracks the full context of an investigation including:
    - Messages exchanged with the LLM
    - Current phase of investigation
    - Collected data and findings
    - Human review requirements
    """
    # Message history (using add_messages reducer for proper updates)
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # Investigation metadata
    topic: str
    depth: str  # quick, standard, deep
    phase: InvestigationPhase
    
    # Collected data
    findings: List[Dict[str, Any]]
    sources: List[str]
    indicators: List[str]  # IOCs, usernames, domains, etc.
    
    # Human-in-the-loop
    requires_human_review: bool
    human_approved: bool
    review_reason: Optional[str]
    
    # Execution tracking
    agents_used: List[str]
    start_time: str
    error: Optional[str]


class SimpleAgentState(TypedDict):
    """Simplified state for single-agent operations."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    query: str
    result: Optional[str]


# =============================================================================
# Checkpoint Configuration
# =============================================================================

def get_checkpointer():
    """
    Get a checkpointer for state persistence.
    
    Uses MemorySaver for in-memory checkpoints.
    In production, could use SQLite, PostgreSQL, or Redis.
    """
    return MemorySaver()


# =============================================================================
# LangGraph Agent Builder
# =============================================================================

class LangGraphAgentBuilder:
    """
    Builder for LangGraph-based agents with advanced features.
    
    Features:
    - State management with typed state
    - Tool integration with ToolNode
    - Human-in-the-loop checkpoints
    - Error handling and retry logic
    """
    
    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0,
    ):
        """
        Initialize the agent builder.
        
        Args:
            model_name: OpenAI model to use
            temperature: Temperature for generation
        """
        self.model_name = model_name
        self.temperature = temperature
        self.checkpointer = get_checkpointer()
        self._llm = None
    
    @property
    def llm(self) -> ChatOpenAI:
        """Lazy-load the LLM."""
        if self._llm is None:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not configured")
            
            self._llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=SecretStr(api_key)
            )
        return self._llm
    
    def build_react_agent(
        self,
        tools: List[BaseTool],
        system_prompt: str,
        with_checkpoints: bool = True,
    ) -> CompiledGraph:
        """
        Build a ReAct agent using LangGraph.
        
        This creates a graph that:
        1. Receives messages
        2. Calls LLM to decide on action
        3. Executes tools if needed
        4. Returns to LLM for next action
        5. Continues until LLM decides to respond
        
        Args:
            tools: List of tools the agent can use
            system_prompt: System prompt for the agent
            with_checkpoints: Whether to enable checkpoints
            
        Returns:
            Compiled StateGraph
        """
        # Bind tools to LLM
        llm_with_tools = self.llm.bind_tools(tools)
        
        # Create tool node
        tool_node = ToolNode(tools)
        
        # Define the agent node
        def agent_node(state: SimpleAgentState) -> dict:
            """Call the LLM with current messages."""
            messages = list(state["messages"])
            
            # Add system prompt as first message if not present
            if not messages or not isinstance(messages[0], HumanMessage) or "You are" not in str(messages[0].content):
                system_msg = HumanMessage(content=f"System: {system_prompt}")
                messages = [system_msg] + messages
            
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}
        
        # Build the graph
        graph = StateGraph(SimpleAgentState)
        
        # Add nodes
        graph.add_node("agent", agent_node)
        graph.add_node("tools", tool_node)
        
        # Add edges
        graph.add_edge(START, "agent")
        graph.add_conditional_edges(
            "agent",
            tools_condition,
            {
                "tools": "tools",
                END: END,
            }
        )
        graph.add_edge("tools", "agent")
        
        # Compile with or without checkpoints
        if with_checkpoints:
            return graph.compile(checkpointer=self.checkpointer)
        return graph.compile()
    
    def build_investigation_graph(
        self,
        tools: List[BaseTool],
        human_review_required: bool = False,
    ) -> CompiledGraph:
        """
        Build a multi-phase investigation graph.
        
        Phases:
        1. Planning - Analyze query and plan investigation
        2. Collection - Use tools to gather information
        3. Analysis - Synthesize findings
        4. Verification - (Optional) Human review
        5. Reporting - Generate final report
        
        Args:
            tools: Tools available for investigation
            human_review_required: Whether human review is mandatory
            
        Returns:
            Compiled StateGraph
        """
        llm_with_tools = self.llm.bind_tools(tools)
        tool_node = ToolNode(tools)
        
        # Planning node
        def planning_node(state: InvestigationState) -> dict:
            """Plan the investigation approach."""
            topic = state["topic"]
            depth = state.get("depth", "standard")
            
            prompt = f"""Plan an OSINT investigation for: {topic}

Investigation depth: {depth}
Available tools: {[t.name for t in tools]}

Create a step-by-step investigation plan. Then begin executing it."""
            
            messages = list(state["messages"]) + [HumanMessage(content=prompt)]
            response = llm_with_tools.invoke(messages)
            
            return {
                "messages": [response],
                "phase": InvestigationPhase.COLLECTION,
            }
        
        # Collection node (agent with tools)
        def collection_node(state: InvestigationState) -> dict:
            """Collect information using tools."""
            messages = list(state["messages"])
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}
        
        # Analysis node
        def analysis_node(state: InvestigationState) -> dict:
            """Analyze and synthesize collected information."""
            messages = list(state["messages"])
            
            analysis_prompt = HumanMessage(content="""Now analyze all the information you've gathered.

1. Summarize key findings
2. Identify patterns and connections
3. Note any indicators of compromise (IOCs)
4. Assess reliability of sources
5. Highlight any gaps in information

Provide your analysis.""")
            
            messages.append(analysis_prompt)
            response = self.llm.invoke(messages)
            
            return {
                "messages": [analysis_prompt, response],
                "phase": InvestigationPhase.VERIFICATION if state.get("requires_human_review") else InvestigationPhase.REPORTING,
            }
        
        # Human review node (interrupt point)
        def human_review_node(state: InvestigationState) -> dict:
            """Pause for human review of sensitive findings."""
            # This node will cause the graph to pause
            # The human can then approve or reject
            review_msg = AIMessage(content=f"""
⚠️ HUMAN REVIEW REQUIRED ⚠️

Reason: {state.get('review_reason', 'Sensitive investigation findings')}

Please review the investigation findings above and:
- Approve to continue to report generation
- Reject to halt the investigation

Awaiting human decision...""")
            
            return {"messages": [review_msg]}
        
        # Reporting node
        def reporting_node(state: InvestigationState) -> dict:
            """Generate the final investigation report."""
            messages = list(state["messages"])
            
            report_prompt = HumanMessage(content="""Generate a comprehensive investigation report.

Structure:
## Investigation Report

### Executive Summary
Brief overview of findings

### Investigation Target
What was investigated

### Methodology  
Agents and tools used

### Findings
Detailed findings organized by category

### Indicators
Any IOCs, usernames, domains, etc. discovered

### Assessment
Analysis and conclusions

### Recommendations
Suggested next steps

Generate the report now.""")
            
            messages.append(report_prompt)
            response = self.llm.invoke(messages)
            
            return {
                "messages": [report_prompt, response],
                "phase": InvestigationPhase.COMPLETE,
            }
        
        # Routing functions
        def should_continue_collection(state: InvestigationState) -> Literal["tools", "analysis"]:
            """Determine if more collection is needed."""
            messages = state["messages"]
            last_message = messages[-1] if messages else None
            
            # Check for tool_calls attribute (AIMessage with tool requests)
            if last_message and isinstance(last_message, AIMessage):
                tool_calls = getattr(last_message, "tool_calls", None)
                if tool_calls:
                    return "tools"
            return "analysis"
        
        def should_require_review(state: InvestigationState) -> Literal["human_review", "reporting"]:
            """Determine if human review is required."""
            if state.get("requires_human_review") and not state.get("human_approved"):
                return "human_review"
            return "reporting"
        
        # Build the graph
        graph = StateGraph(InvestigationState)
        
        # Add nodes
        graph.add_node("planning", planning_node)
        graph.add_node("collection", collection_node)
        graph.add_node("tools", tool_node)
        graph.add_node("analysis", analysis_node)
        graph.add_node("human_review", human_review_node)
        graph.add_node("reporting", reporting_node)
        
        # Add edges
        graph.add_edge(START, "planning")
        graph.add_edge("planning", "collection")
        graph.add_conditional_edges(
            "collection",
            should_continue_collection,
            {
                "tools": "tools",
                "analysis": "analysis",
            }
        )
        graph.add_edge("tools", "collection")
        graph.add_conditional_edges(
            "analysis",
            should_require_review,
            {
                "human_review": "human_review",
                "reporting": "reporting",
            }
        )
        graph.add_edge("human_review", "reporting")  # After human approves
        graph.add_edge("reporting", END)
        
        # Compile with checkpoints and interrupt points
        return graph.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["human_review"] if human_review_required else [],
        )


# =============================================================================
# Utility Functions
# =============================================================================

def create_simple_react_agent(
    tools: List[BaseTool],
    system_prompt: str,
    model_name: str = "gpt-4o-mini",
) -> CompiledGraph:
    """
    Create a simple ReAct agent for quick use.
    
    Args:
        tools: Tools for the agent
        system_prompt: System prompt
        model_name: OpenAI model
        
    Returns:
        Compiled StateGraph
    """
    builder = LangGraphAgentBuilder(model_name=model_name)
    return builder.build_react_agent(tools, system_prompt)


def create_investigation_graph(
    tools: List[BaseTool],
    human_review: bool = False,
    model_name: str = "gpt-4o-mini",
) -> CompiledGraph:
    """
    Create an investigation graph.
    
    Args:
        tools: Tools for investigation
        human_review: Whether to require human review
        model_name: OpenAI model
        
    Returns:
        Compiled StateGraph
    """
    builder = LangGraphAgentBuilder(model_name=model_name)
    return builder.build_investigation_graph(tools, human_review_required=human_review)


async def run_investigation(
    graph: CompiledGraph,
    topic: str,
    depth: str = "standard",
    thread_id: str = "default",
) -> Dict[str, Any]:
    """
    Run an investigation using the graph.
    
    Args:
        graph: Compiled investigation graph
        topic: Topic to investigate
        depth: Investigation depth
        thread_id: Thread ID for state persistence
        
    Returns:
        Investigation results
    """
    initial_state: InvestigationState = {
        "messages": [],
        "topic": topic,
        "depth": depth,
        "phase": InvestigationPhase.PLANNING,
        "findings": [],
        "sources": [],
        "indicators": [],
        "requires_human_review": False,
        "human_approved": False,
        "review_reason": None,
        "agents_used": [],
        "start_time": datetime.now().isoformat(),
        "error": None,
    }
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # Run the graph
    result = await graph.ainvoke(initial_state, config)
    
    # Extract final report from messages
    messages = result.get("messages", [])
    report = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and "## Investigation Report" in str(msg.content):
            report = msg.content
            break
    
    return {
        "success": True,
        "topic": topic,
        "report": report or str(messages[-1].content) if messages else "No report generated",
        "phase": result.get("phase", InvestigationPhase.COMPLETE),
        "metadata": {
            "depth": depth,
            "thread_id": thread_id,
            "start_time": result.get("start_time"),
        }
    }
