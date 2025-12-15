# =============================================================================
# OSINT Agentic Operations - Investigation Tracing
# =============================================================================
"""
Tracing module for recording execution traces during OSINT investigations.

Provides:
- TracingContext: Context manager for trace management
- @traced decorator for automatic tool/function tracing
- Utility functions for evidence recording
"""

import json
import logging
import functools
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from db import TraceRepository, Trace, TraceType, TraceStatus

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class TracingContext:
    """
    Context for managing traces during an investigation.
    
    Maintains the current run_id and parent_trace_id for hierarchical traces.
    """
    
    _current: Optional['TracingContext'] = None
    
    def __init__(self, run_id: int, agent_name: str = None):
        """
        Initialize tracing context.
        
        Args:
            run_id: The investigation run ID
            agent_name: Optional agent name for all traces in this context
        """
        self.run_id = run_id
        self.agent_name = agent_name
        self._parent_trace_id: Optional[int] = None
        self._trace_stack: List[int] = []
        self._previous_context: Optional['TracingContext'] = None
    
    def __enter__(self) -> 'TracingContext':
        """Enter the context and set as current."""
        self._previous_context = TracingContext._current
        TracingContext._current = self
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and restore previous."""
        TracingContext._current = self._previous_context
        return False
    
    @classmethod
    def get_current(cls) -> Optional['TracingContext']:
        """Get the current tracing context."""
        return cls._current
    
    @classmethod
    def get_run_id(cls) -> Optional[int]:
        """Get the current run ID if in a tracing context."""
        current = cls.get_current()
        return current.run_id if current else None
    
    def push_trace(self, trace_id: int):
        """Push a trace ID onto the stack (for nested traces)."""
        if self._trace_stack:
            self._parent_trace_id = self._trace_stack[-1]
        self._trace_stack.append(trace_id)
    
    def pop_trace(self):
        """Pop a trace ID from the stack."""
        if self._trace_stack:
            self._trace_stack.pop()
            if self._trace_stack:
                self._parent_trace_id = self._trace_stack[-1]
            else:
                self._parent_trace_id = None
    
    @property
    def parent_trace_id(self) -> Optional[int]:
        """Get the current parent trace ID."""
        return self._parent_trace_id
    
    def start_trace(
        self,
        trace_type: str,
        tool_name: str = None,
        instruction: str = None,
        input_params: Dict = None,
        agent_name: str = None
    ) -> int:
        """
        Start a new trace.
        
        Args:
            trace_type: Type of trace (from TraceType enum)
            tool_name: Name of the tool being executed
            instruction: Instruction/prompt that triggered this action
            input_params: Input parameters for the tool
            agent_name: Override for agent name
            
        Returns:
            The new trace ID
        """
        trace_id = TraceRepository.start_trace(
            run_id=self.run_id,
            trace_type=trace_type,
            agent_name=agent_name or self.agent_name,
            tool_name=tool_name,
            instruction=instruction,
            input_params=input_params,
            parent_trace_id=self._parent_trace_id
        )
        self.push_trace(trace_id)
        return trace_id
    
    def complete_trace(
        self,
        trace_id: int = None,
        output: Any = None,
        evidence: List[Dict] = None,
        confidence: float = None,
        reasoning: str = None
    ):
        """
        Complete a trace with results.
        
        Args:
            trace_id: ID of trace to complete (or current if None)
            output: Output data from the tool
            evidence: Evidence findings
            confidence: Confidence score (0-1)
            reasoning: LLM reasoning for this step
        """
        if trace_id is None and self._trace_stack:
            trace_id = self._trace_stack[-1]
        
        if trace_id:
            TraceRepository.complete_trace(
                trace_id=trace_id,
                output=output,
                evidence=evidence,
                confidence=confidence,
                reasoning=reasoning
            )
            self.pop_trace()
    
    def fail_trace(
        self,
        trace_id: int = None,
        error_message: str = "",
        error_type: str = None
    ):
        """
        Mark a trace as failed.
        
        Args:
            trace_id: ID of trace to fail (or current if None)
            error_message: Error description
            error_type: Type of error
        """
        if trace_id is None and self._trace_stack:
            trace_id = self._trace_stack[-1]
        
        if trace_id:
            TraceRepository.fail_trace(
                trace_id=trace_id,
                error_message=error_message,
                error_type=error_type
            )
            self.pop_trace()
    
    def add_decision(
        self,
        decision: str,
        reasoning: str = None,
        options_considered: List[str] = None
    ) -> int:
        """
        Record a decision point in the investigation.
        
        Args:
            decision: The decision made
            reasoning: Why this decision was made
            options_considered: Other options that were considered
            
        Returns:
            The trace ID
        """
        trace_id = self.start_trace(
            trace_type=TraceType.DECISION.value,
            instruction=decision,
            input_params={"options_considered": options_considered} if options_considered else None
        )
        self.complete_trace(
            trace_id=trace_id,
            reasoning=reasoning
        )
        return trace_id
    
    def add_reasoning(self, reasoning: str, context: Dict = None) -> int:
        """
        Record LLM reasoning step.
        
        Args:
            reasoning: The reasoning content
            context: Additional context
            
        Returns:
            The trace ID
        """
        trace_id = self.start_trace(
            trace_type=TraceType.LLM_REASONING.value,
            instruction=reasoning[:200] + "..." if len(reasoning) > 200 else reasoning,
            input_params=context
        )
        self.complete_trace(trace_id=trace_id, reasoning=reasoning)
        return trace_id
    
    def add_checkpoint(self, name: str, state: Dict = None) -> int:
        """
        Record a checkpoint in the investigation.
        
        Args:
            name: Checkpoint name
            state: Current state to save
            
        Returns:
            The trace ID
        """
        trace_id = self.start_trace(
            trace_type=TraceType.CHECKPOINT.value,
            tool_name=name,
            input_params=state
        )
        self.complete_trace(trace_id=trace_id)
        return trace_id


def traced(
    trace_type: str = TraceType.TOOL_CALL.value,
    tool_name: str = None,
    extract_evidence: Callable[[Any], List[Dict]] = None
) -> Callable[[F], F]:
    """
    Decorator to automatically trace function execution.
    
    Args:
        trace_type: Type of trace to create
        tool_name: Override for tool name (default: function name)
        extract_evidence: Optional function to extract evidence from result
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            ctx = TracingContext.get_current()
            
            if ctx is None:
                # No tracing context, just run the function
                return func(*args, **kwargs)
            
            # Start trace
            name = tool_name or func.__name__
            trace_id = ctx.start_trace(
                trace_type=trace_type,
                tool_name=name,
                input_params={
                    "args": [str(a)[:100] for a in args],
                    "kwargs": {k: str(v)[:100] for k, v in kwargs.items()}
                }
            )
            
            try:
                result = func(*args, **kwargs)
                
                # Extract evidence if extractor provided
                evidence = None
                if extract_evidence:
                    try:
                        evidence = extract_evidence(result)
                    except Exception:
                        pass
                
                ctx.complete_trace(
                    trace_id=trace_id,
                    output=_serialize_output(result),
                    evidence=evidence
                )
                
                return result
                
            except Exception as e:
                ctx.fail_trace(
                    trace_id=trace_id,
                    error_message=str(e),
                    error_type=type(e).__name__
                )
                raise
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            ctx = TracingContext.get_current()
            
            if ctx is None:
                return await func(*args, **kwargs)
            
            name = tool_name or func.__name__
            trace_id = ctx.start_trace(
                trace_type=trace_type,
                tool_name=name,
                input_params={
                    "args": [str(a)[:100] for a in args],
                    "kwargs": {k: str(v)[:100] for k, v in kwargs.items()}
                }
            )
            
            try:
                result = await func(*args, **kwargs)
                
                evidence = None
                if extract_evidence:
                    try:
                        evidence = extract_evidence(result)
                    except Exception:
                        pass
                
                ctx.complete_trace(
                    trace_id=trace_id,
                    output=_serialize_output(result),
                    evidence=evidence
                )
                
                return result
                
            except Exception as e:
                ctx.fail_trace(
                    trace_id=trace_id,
                    error_message=str(e),
                    error_type=type(e).__name__
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore
    
    return decorator


def _serialize_output(output: Any, max_length: int = 5000) -> Any:
    """
    Serialize output data for storage.
    
    Args:
        output: The output to serialize
        max_length: Maximum length for string outputs
        
    Returns:
        Serializable representation of output
    """
    if output is None:
        return None
    
    if isinstance(output, (str, int, float, bool)):
        if isinstance(output, str) and len(output) > max_length:
            return output[:max_length] + f"... [truncated, {len(output)} total chars]"
        return output
    
    if isinstance(output, (list, tuple)):
        return [_serialize_output(item, max_length // 10) for item in output[:20]]
    
    if isinstance(output, dict):
        return {
            k: _serialize_output(v, max_length // 10) 
            for k, v in list(output.items())[:20]
        }
    
    if hasattr(output, 'to_dict'):
        return _serialize_output(output.to_dict(), max_length)
    
    if hasattr(output, '__dict__'):
        return _serialize_output(output.__dict__, max_length)
    
    return str(output)[:max_length]


@contextmanager
def trace_investigation(run_id: int, agent_name: str = None):
    """
    Context manager for tracing an entire investigation.
    
    Usage:
        with trace_investigation(run_id=42, agent_name="ControlAgent") as ctx:
            # All tool calls within this block will be traced
            result = some_tool.run(query)
            
            # Can also manually add traces
            ctx.add_decision("Selected SearchAgent for web search")
    
    Args:
        run_id: The investigation run ID
        agent_name: Default agent name for traces
        
    Yields:
        TracingContext instance
    """
    ctx = TracingContext(run_id=run_id, agent_name=agent_name)
    
    with ctx:
        # Add initial checkpoint
        ctx.add_checkpoint("investigation_started", {"run_id": run_id})
        
        try:
            yield ctx
            
            # Add completion checkpoint
            ctx.add_checkpoint("investigation_completed")
            
        except Exception as e:
            # Record error
            ctx.start_trace(
                trace_type=TraceType.ERROR.value,
                instruction="Investigation error",
                input_params={"error": str(e), "type": type(e).__name__}
            )
            ctx.fail_trace(error_message=str(e), error_type=type(e).__name__)
            raise


def record_tool_call(
    run_id: int,
    tool_name: str,
    input_params: Dict,
    output: Any,
    evidence: List[Dict] = None,
    agent_name: str = None,
    instruction: str = None,
    confidence: float = None
) -> int:
    """
    Convenience function to record a single tool call trace.
    
    Args:
        run_id: Investigation run ID
        tool_name: Name of the tool
        input_params: Input parameters
        output: Tool output
        evidence: Evidence found
        agent_name: Agent that made the call
        instruction: Instruction that triggered the call
        confidence: Confidence score
        
    Returns:
        Trace ID
    """
    trace_id = TraceRepository.start_trace(
        run_id=run_id,
        trace_type=TraceType.TOOL_CALL.value,
        tool_name=tool_name,
        agent_name=agent_name,
        instruction=instruction,
        input_params=input_params
    )
    
    TraceRepository.complete_trace(
        trace_id=trace_id,
        output=_serialize_output(output),
        evidence=evidence,
        confidence=confidence
    )
    
    return trace_id


def record_agent_action(
    run_id: int,
    agent_name: str,
    action: str,
    reasoning: str = None,
    result: Any = None,
    evidence: List[Dict] = None
) -> int:
    """
    Record an agent action trace.
    
    Args:
        run_id: Investigation run ID
        agent_name: Name of the agent
        action: Description of the action
        reasoning: Why the action was taken
        result: Action result
        evidence: Evidence found
        
    Returns:
        Trace ID
    """
    trace_id = TraceRepository.start_trace(
        run_id=run_id,
        trace_type=TraceType.AGENT_ACTION.value,
        agent_name=agent_name,
        instruction=action
    )
    
    TraceRepository.complete_trace(
        trace_id=trace_id,
        output=_serialize_output(result),
        evidence=evidence,
        reasoning=reasoning
    )
    
    return trace_id
