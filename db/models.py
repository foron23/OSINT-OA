# =============================================================================
# OSINT Agentic Operations - Database Models
# =============================================================================
"""
Data Transfer Objects (DTOs) and model helpers for OSINT investigations.
Includes models for runs, traces, evidence, indicators, and reports.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import hashlib


class RunStatus(str, Enum):
    """Status of a collection run."""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class TraceType(str, Enum):
    """Type of trace/execution step."""
    TOOL_CALL = "tool_call"
    AGENT_ACTION = "agent_action"
    LLM_REASONING = "llm_reasoning"
    DECISION = "decision"
    ERROR = "error"
    CHECKPOINT = "checkpoint"


class TraceStatus(str, Enum):
    """Status of a trace execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ItemType(str, Enum):
    """Type of OSINT item."""
    ARTICLE = "article"
    MENTION = "mention"
    REPORT = "report"
    OTHER = "other"


class IndicatorType(str, Enum):
    """Type of indicator/IOC."""
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    HASH = "hash"
    EMAIL = "email"
    CVE = "cve"
    HANDLE = "handle"
    OTHER = "other"


class SourceKind(str, Enum):
    """Kind of data source."""
    SEARCH = "search"
    CLI = "cli"
    RSS = "rss"
    WEB = "web"
    API = "api"
    OTHER = "other"


# =============================================================================
# Data Transfer Objects
# =============================================================================

@dataclass
class Source:
    """Represents a data source."""
    id: Optional[int] = None
    name: str = ""
    kind: str = SourceKind.OTHER.value
    base_url: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_row(cls, row) -> "Source":
        if row is None:
            return None
        row_dict = dict(row) if hasattr(row, 'keys') else row
        return cls(
            id=row_dict["id"],
            name=row_dict["name"],
            kind=row_dict["kind"],
            base_url=row_dict.get("base_url"),
            description=row_dict.get("description"),
            created_at=row_dict.get("created_at")
        )


@dataclass
class Run:
    """Represents a collection run/investigation."""
    id: Optional[int] = None
    query: str = ""
    since: Optional[str] = None
    until: Optional[str] = None
    limit_requested: Optional[int] = None
    status: str = RunStatus.STARTED.value
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    stats_json: Optional[str] = None
    scope: Optional[str] = None
    initiated_by: str = "api"
    
    def to_dict(self) -> dict:
        d = asdict(self)
        if self.stats_json:
            try:
                d["stats"] = json.loads(self.stats_json)
            except:
                d["stats"] = None
        return d
    
    @classmethod
    def from_row(cls, row) -> "Run":
        if row is None:
            return None
        row_dict = dict(row) if hasattr(row, 'keys') else row
        return cls(
            id=row_dict["id"],
            query=row_dict["query"],
            since=row_dict.get("since"),
            until=row_dict.get("until"),
            limit_requested=row_dict.get("limit_requested"),
            status=row_dict["status"],
            started_at=row_dict.get("started_at"),
            finished_at=row_dict.get("finished_at"),
            stats_json=row_dict.get("stats_json"),
            scope=row_dict.get("scope"),
            initiated_by=row_dict.get("initiated_by", "api")
        )


@dataclass
class Trace:
    """
    Represents a single execution trace in an investigation.
    Captures tool calls, agent decisions, LLM reasoning, and evidence found.
    """
    id: Optional[int] = None
    run_id: Optional[int] = None
    parent_trace_id: Optional[int] = None  # For hierarchical traces
    sequence_number: int = 0  # Order within the run
    
    # Execution context
    trace_type: str = TraceType.TOOL_CALL.value
    agent_name: Optional[str] = None
    tool_name: Optional[str] = None
    
    # Instruction/prompt that triggered this action
    instruction: Optional[str] = None
    reasoning: Optional[str] = None  # LLM's reasoning for this action
    
    # Input/Output data
    input_params_json: Optional[str] = None  # JSON serialized input
    output_data_json: Optional[str] = None   # JSON serialized output
    
    # Evidence tracking
    evidence_found_json: Optional[str] = None  # Key findings as JSON array
    evidence_count: int = 0
    confidence_score: Optional[float] = None  # 0.0 to 1.0
    
    # Execution timing
    status: str = TraceStatus.PENDING.value
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_ms: Optional[int] = None
    
    # Error handling
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # Metadata
    metadata_json: Optional[str] = None
    created_at: Optional[str] = None
    
    def to_dict(self, include_full_data: bool = True) -> dict:
        """Convert to dictionary, optionally including full JSON data."""
        d = {
            "id": self.id,
            "run_id": self.run_id,
            "parent_trace_id": self.parent_trace_id,
            "sequence_number": self.sequence_number,
            "trace_type": self.trace_type,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name,
            "instruction": self.instruction,
            "reasoning": self.reasoning,
            "evidence_count": self.evidence_count,
            "confidence_score": self.confidence_score,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "created_at": self.created_at
        }
        
        if include_full_data:
            # Parse JSON fields
            for json_field in ["input_params_json", "output_data_json", 
                              "evidence_found_json", "metadata_json"]:
                raw = getattr(self, json_field)
                key = json_field.replace("_json", "")
                if raw:
                    try:
                        d[key] = json.loads(raw)
                    except:
                        d[key] = None
                else:
                    d[key] = None
        
        return d
    
    @classmethod
    def from_row(cls, row) -> "Trace":
        """Create Trace from database row."""
        if row is None:
            return None
        row_dict = dict(row) if hasattr(row, 'keys') else row
        return cls(
            id=row_dict["id"],
            run_id=row_dict.get("run_id"),
            parent_trace_id=row_dict.get("parent_trace_id"),
            sequence_number=row_dict.get("sequence_number", 0),
            trace_type=row_dict.get("trace_type", TraceType.TOOL_CALL.value),
            agent_name=row_dict.get("agent_name"),
            tool_name=row_dict.get("tool_name"),
            instruction=row_dict.get("instruction"),
            reasoning=row_dict.get("reasoning"),
            input_params_json=row_dict.get("input_params_json"),
            output_data_json=row_dict.get("output_data_json"),
            evidence_found_json=row_dict.get("evidence_found_json"),
            evidence_count=row_dict.get("evidence_count", 0),
            confidence_score=row_dict.get("confidence_score"),
            status=row_dict.get("status", TraceStatus.PENDING.value),
            started_at=row_dict.get("started_at"),
            finished_at=row_dict.get("finished_at"),
            duration_ms=row_dict.get("duration_ms"),
            error_message=row_dict.get("error_message"),
            error_type=row_dict.get("error_type"),
            metadata_json=row_dict.get("metadata_json"),
            created_at=row_dict.get("created_at")
        )
    
    def set_input_params(self, params: Dict[str, Any]):
        """Set input parameters from dict."""
        self.input_params_json = json.dumps(params) if params else None
    
    def set_output_data(self, data: Any):
        """Set output data from any serializable object."""
        self.output_data_json = json.dumps(data) if data else None
    
    def add_evidence(self, evidence: List[Dict[str, Any]]):
        """Add evidence findings."""
        self.evidence_found_json = json.dumps(evidence) if evidence else None
        self.evidence_count = len(evidence) if evidence else 0
    
    def set_metadata(self, metadata: Dict[str, Any]):
        """Set metadata from dict."""
        self.metadata_json = json.dumps(metadata) if metadata else None
    
    def complete(self, output: Any = None, evidence: List[Dict] = None,
                 confidence: float = None):
        """Mark trace as completed with results."""
        self.status = TraceStatus.COMPLETED.value
        self.finished_at = datetime.utcnow().isoformat()
        if self.started_at:
            try:
                start = datetime.fromisoformat(self.started_at.replace('Z', '+00:00'))
                end = datetime.fromisoformat(self.finished_at)
                self.duration_ms = int((end - start).total_seconds() * 1000)
            except:
                pass
        if output is not None:
            self.set_output_data(output)
        if evidence:
            self.add_evidence(evidence)
        if confidence is not None:
            self.confidence_score = confidence
    
    def fail(self, error_message: str, error_type: str = None):
        """Mark trace as failed with error."""
        self.status = TraceStatus.FAILED.value
        self.finished_at = datetime.utcnow().isoformat()
        self.error_message = error_message
        self.error_type = error_type or "UnknownError"
        if self.started_at:
            try:
                start = datetime.fromisoformat(self.started_at.replace('Z', '+00:00'))
                end = datetime.fromisoformat(self.finished_at)
                self.duration_ms = int((end - start).total_seconds() * 1000)
            except:
                pass


@dataclass
class Item:
    """Represents an OSINT item/evidence."""
    id: Optional[int] = None
    run_id: Optional[int] = None
    source_id: Optional[int] = None
    title: str = ""
    summary: str = ""
    url: str = ""
    image_url: Optional[str] = None
    published_at: Optional[str] = None
    item_type: str = ItemType.ARTICLE.value
    language: Optional[str] = None
    content_hash: Optional[str] = None
    raw_data: Optional[str] = None
    created_at: Optional[str] = None
    
    # Related data (populated on demand)
    tags: List[str] = field(default_factory=list)
    indicators: List["Indicator"] = field(default_factory=list)
    source: Optional[Source] = None
    
    def compute_content_hash(self) -> str:
        """Compute a hash of the content for deduplication."""
        content = f"{self.title}|{self.summary}|{self.url}"
        self.content_hash = hashlib.sha256(content.encode()).hexdigest()[:32]
        return self.content_hash
    
    def to_dict(self, include_relations: bool = True) -> dict:
        d = asdict(self)
        if self.raw_data:
            try:
                d["raw"] = json.loads(self.raw_data)
            except:
                d["raw"] = None
        
        if include_relations:
            d["tags"] = self.tags
            d["indicators"] = [i.to_dict() for i in self.indicators] if self.indicators else []
            d["source"] = self.source.to_dict() if self.source else None
        else:
            d.pop("tags", None)
            d.pop("indicators", None)
            d.pop("source", None)
        
        return d
    
    @classmethod
    def from_row(cls, row) -> "Item":
        if row is None:
            return None
        # Convert sqlite3.Row to dict for .get() access
        row_dict = dict(row) if hasattr(row, 'keys') else row
        return cls(
            id=row_dict["id"],
            run_id=row_dict["run_id"],
            source_id=row_dict["source_id"],
            title=row_dict["title"],
            summary=row_dict["summary"],
            url=row_dict["url"],
            image_url=row_dict.get("image_url"),
            published_at=row_dict.get("published_at"),
            item_type=row_dict.get("item_type", "article"),
            language=row_dict.get("language"),
            content_hash=row_dict.get("content_hash"),
            raw_data=row_dict.get("raw_data"),
            created_at=row_dict.get("created_at")
        )


@dataclass
class Indicator:
    """Represents an IOC/indicator."""
    id: Optional[int] = None
    type: str = IndicatorType.OTHER.value
    value: str = ""
    normalized_value: Optional[str] = None
    confidence: Optional[float] = None
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None
    metadata_json: Optional[str] = None
    
    # Related items (populated on demand)
    items: List[Item] = field(default_factory=list)
    
    def to_dict(self, include_items: bool = False) -> dict:
        d = asdict(self)
        if self.metadata_json:
            try:
                d["metadata"] = json.loads(self.metadata_json)
            except:
                d["metadata"] = None
        
        if include_items:
            d["items"] = [i.to_dict(include_relations=False) for i in self.items]
        else:
            d.pop("items", None)
        
        return d
    
    @classmethod
    def from_row(cls, row) -> "Indicator":
        if row is None:
            return None
        row_dict = dict(row) if hasattr(row, 'keys') else row
        return cls(
            id=row_dict["id"],
            type=row_dict["type"],
            value=row_dict["value"],
            normalized_value=row_dict.get("normalized_value"),
            confidence=row_dict.get("confidence"),
            first_seen_at=row_dict.get("first_seen_at"),
            last_seen_at=row_dict.get("last_seen_at"),
            metadata_json=row_dict.get("metadata_json")
        )


@dataclass
class Tag:
    """Represents a tag for classification."""
    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_row(cls, row) -> "Tag":
        if row is None:
            return None
        row_dict = dict(row) if hasattr(row, 'keys') else row
        return cls(
            id=row_dict["id"],
            name=row_dict["name"],
            description=row_dict.get("description"),
            created_at=row_dict.get("created_at")
        )


@dataclass
class Report:
    """Represents a generated report."""
    id: Optional[int] = None
    run_id: Optional[int] = None
    query: str = ""
    report: str = ""
    summary: Optional[str] = None
    stats_json: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_message_id: Optional[str] = None
    published_at: Optional[str] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        if self.stats_json:
            try:
                d["stats"] = json.loads(self.stats_json)
            except:
                d["stats"] = None
        return d
    
    @classmethod
    def from_row(cls, row) -> "Report":
        if row is None:
            return None
        row_dict = dict(row) if hasattr(row, 'keys') else row
        return cls(
            id=row_dict["id"],
            run_id=row_dict.get("run_id"),
            query=row_dict["query"],
            report=row_dict["report"],
            summary=row_dict.get("summary"),
            stats_json=row_dict.get("stats_json"),
            telegram_chat_id=row_dict.get("telegram_chat_id"),
            telegram_message_id=row_dict.get("telegram_message_id"),
            published_at=row_dict.get("published_at"),
            created_at=row_dict.get("created_at")
        )


# =============================================================================
# OSINT Result DTO (for agent communication)
# =============================================================================

@dataclass
class OsintResult:
    """
    Normalized OSINT result from an agent.
    This is the common format that all agents must return.
    """
    title: str
    summary: str
    url: str
    source_name: str  # Name of the source (e.g., "Google", "Recon-ng")
    published_at: Optional[str] = None
    image_url: Optional[str] = None
    item_type: str = ItemType.ARTICLE.value
    language: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    indicators: List[Dict[str, Any]] = field(default_factory=list)  # [{type, value, confidence}]
    raw_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_item(self, run_id: int = None, source_id: int = None) -> Item:
        """Convert to an Item for database storage."""
        item = Item(
            run_id=run_id,
            source_id=source_id,
            title=self.title,
            summary=self.summary,
            url=self.url,
            image_url=self.image_url,
            published_at=self.published_at,
            item_type=self.item_type,
            language=self.language,
            raw_data=json.dumps(self.raw_data) if self.raw_data else None,
            tags=self.tags
        )
        item.compute_content_hash()
        return item


@dataclass
class OsintReport:
    """Report DTO for the Validator output."""
    query: str
    summary: str
    report_markdown: str
    total_items: int
    total_indicators: int
    sources_used: List[str]
    tags_found: List[str]
    run_id: Optional[int] = None
    stats: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


# =============================================================================
# Task Planning DTOs (for Strategist Agent)
# =============================================================================

@dataclass
class OsintTask:
    """A single OSINT task to be executed by an agent."""
    agent_name: str
    inputs: Dict[str, Any]  # query, target, etc.
    constraints: Dict[str, Any] = field(default_factory=dict)  # timeout, limit, scope
    priority: int = 1  # 1 = highest
    status: str = "pending"  # pending|running|completed|failed
    result: Optional[Any] = None
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TaskPlan:
    """Execution plan from the Strategist Agent."""
    objective: str
    tasks: List[OsintTask]
    completion_criteria: Dict[str, Any]  # min_results, min_sources, timeout
    scope: str  # allowed scope for this investigation
    priority_order: List[str] = field(default_factory=list)  # agent names in order
    
    def to_dict(self) -> dict:
        return {
            "objective": self.objective,
            "tasks": [t.to_dict() for t in self.tasks],
            "completion_criteria": self.completion_criteria,
            "scope": self.scope,
            "priority_order": self.priority_order
        }
