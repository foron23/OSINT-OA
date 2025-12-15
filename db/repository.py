# =============================================================================
# OSINT Agentic Operations - Database Repository
# =============================================================================
"""
Repository pattern implementation for database operations.
Handles all CRUD operations for investigations, traces, evidence, and reports.
"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from db.sqlite import get_db
from db.models import (
    Run, RunStatus, Item, Indicator, Tag, Source, Report, OsintResult
)


class RunRepository:
    """Repository for Run operations."""
    
    @staticmethod
    def create(query: str, since: str = None, until: str = None, 
               limit_requested: int = None, scope: str = None,
               initiated_by: str = "api") -> int:
        """Create a new run and return its ID."""
        db = get_db()
        return db.insert(
            """INSERT INTO runs (query, since, until, limit_requested, scope, initiated_by, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (query, since, until, limit_requested, scope, initiated_by, RunStatus.STARTED.value)
        )
    
    @staticmethod
    def get_by_id(run_id: int) -> Optional[Run]:
        """Get a run by ID."""
        db = get_db()
        row = db.execute_one("SELECT * FROM runs WHERE id = ?", (run_id,))
        return Run.from_row(row)
    
    @staticmethod
    def update_status(run_id: int, status: str, stats: Dict = None):
        """Update run status and optionally stats."""
        db = get_db()
        stats_json = json.dumps(stats) if stats else None
        finished_at = datetime.utcnow().isoformat() if status in ['completed', 'failed', 'partial'] else None
        
        db.update(
            """UPDATE runs SET status = ?, stats_json = ?, finished_at = ? WHERE id = ?""",
            (status, stats_json, finished_at, run_id)
        )
    
    @staticmethod
    def list_runs(q: str = None, status: str = None, since: str = None, 
                  until: str = None, limit: int = 50, offset: int = 0) -> List[Run]:
        """List runs with optional filters."""
        db = get_db()
        conditions = []
        params = []
        
        if q:
            conditions.append("query LIKE ?")
            params.append(f"%{q}%")
        if status:
            conditions.append("status = ?")
            params.append(status)
        if since:
            conditions.append("started_at >= ?")
            params.append(since)
        if until:
            conditions.append("started_at <= ?")
            params.append(until)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""SELECT * FROM runs WHERE {where_clause} 
                   ORDER BY started_at DESC LIMIT ? OFFSET ?"""
        params.extend([limit, offset])
        
        rows = db.execute(query, tuple(params))
        return [Run.from_row(row) for row in rows]
    
    @staticmethod
    def delete(run_id: int) -> bool:
        """Delete a run and all related data (cascade)."""
        db = get_db()
        count = db.update("DELETE FROM runs WHERE id = ?", (run_id,))
        return count > 0


class SourceRepository:
    """Repository for Source operations."""
    
    @staticmethod
    def get_by_name(name: str) -> Optional[Source]:
        """Get a source by name."""
        db = get_db()
        row = db.execute_one("SELECT * FROM sources WHERE name = ?", (name,))
        return Source.from_row(row)
    
    @staticmethod
    def get_or_create(name: str, kind: str = "other") -> int:
        """Get source ID by name or create if not exists."""
        source = SourceRepository.get_by_name(name)
        if source:
            return source.id
        
        db = get_db()
        return db.insert(
            "INSERT INTO sources (name, kind) VALUES (?, ?)",
            (name, kind)
        )
    
    @staticmethod
    def list_all() -> List[Source]:
        """List all sources."""
        db = get_db()
        rows = db.execute("SELECT * FROM sources ORDER BY name")
        return [Source.from_row(row) for row in rows]


class ItemRepository:
    """Repository for Item operations."""
    
    @staticmethod
    def create(item: Item) -> int:
        """Create a new item and return its ID."""
        db = get_db()
        
        # Compute content hash if not set
        if not item.content_hash:
            item.compute_content_hash()
        
        return db.insert(
            """INSERT OR REPLACE INTO items 
               (run_id, source_id, title, summary, url, image_url, published_at, 
                item_type, language, content_hash, raw_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item.run_id, item.source_id, item.title, item.summary, item.url,
             item.image_url, item.published_at, item.item_type, item.language,
             item.content_hash, item.raw_data)
        )
    
    @staticmethod
    def create_from_osint_result(result: OsintResult, run_id: int) -> int:
        """Create an item from an OsintResult."""
        # Get or create source
        source_id = SourceRepository.get_or_create(result.source_name)
        
        # Convert to Item
        item = result.to_item(run_id=run_id, source_id=source_id)
        item_id = ItemRepository.create(item)
        
        # Add tags
        for tag_name in result.tags:
            tag_id = TagRepository.get_or_create(tag_name)
            ItemRepository.add_tag(item_id, tag_id)
        
        # Add indicators
        for ind_data in result.indicators:
            indicator = Indicator(
                type=ind_data.get("type", "other"),
                value=ind_data.get("value", ""),
                confidence=ind_data.get("confidence")
            )
            ind_id = IndicatorRepository.get_or_create(indicator)
            ItemRepository.add_indicator(item_id, ind_id, ind_data.get("context"))
        
        return item_id
    
    @staticmethod
    def get_by_id(item_id: int, include_relations: bool = True) -> Optional[Item]:
        """Get an item by ID with optional relations."""
        db = get_db()
        row = db.execute_one("SELECT * FROM items WHERE id = ?", (item_id,))
        if not row:
            return None
        
        item = Item.from_row(row)
        
        if include_relations:
            # Get source
            if item.source_id:
                source_row = db.execute_one("SELECT * FROM sources WHERE id = ?", (item.source_id,))
                item.source = Source.from_row(source_row)
            
            # Get tags
            tag_rows = db.execute(
                """SELECT t.name FROM tags t 
                   JOIN item_tags it ON t.id = it.tag_id 
                   WHERE it.item_id = ?""",
                (item_id,)
            )
            item.tags = [row["name"] for row in tag_rows]
            
            # Get indicators
            ind_rows = db.execute(
                """SELECT i.* FROM indicators i 
                   JOIN item_indicators ii ON i.id = ii.indicator_id 
                   WHERE ii.item_id = ?""",
                (item_id,)
            )
            item.indicators = [Indicator.from_row(row) for row in ind_rows]
        
        return item
    
    @staticmethod
    def list_items(q: str = None, source: str = None, tag: str = None,
                   indicator_type: str = None, indicator_value: str = None,
                   run_id: int = None, since: str = None, until: str = None,
                   limit: int = 50, offset: int = 0) -> List[Item]:
        """List items with optional filters."""
        db = get_db()
        conditions = []
        params = []
        joins = []
        
        if q:
            conditions.append("(i.title LIKE ? OR i.summary LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        
        if source:
            joins.append("JOIN sources s ON i.source_id = s.id")
            conditions.append("s.name = ?")
            params.append(source)
        
        if tag:
            joins.append("JOIN item_tags it ON i.id = it.item_id")
            joins.append("JOIN tags t ON it.tag_id = t.id")
            conditions.append("t.name = ?")
            params.append(tag)
        
        if indicator_type or indicator_value:
            joins.append("JOIN item_indicators ii ON i.id = ii.item_id")
            joins.append("JOIN indicators ind ON ii.indicator_id = ind.id")
            if indicator_type:
                conditions.append("ind.type = ?")
                params.append(indicator_type)
            if indicator_value:
                conditions.append("ind.value LIKE ?")
                params.append(f"%{indicator_value}%")
        
        if run_id:
            conditions.append("i.run_id = ?")
            params.append(run_id)
        
        if since:
            conditions.append("i.published_at >= ?")
            params.append(since)
        
        if until:
            conditions.append("i.published_at <= ?")
            params.append(until)
        
        join_clause = " ".join(joins)
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""SELECT DISTINCT i.* FROM items i {join_clause}
                   WHERE {where_clause} 
                   ORDER BY i.published_at DESC NULLS LAST, i.created_at DESC
                   LIMIT ? OFFSET ?"""
        params.extend([limit, offset])
        
        rows = db.execute(query, tuple(params))
        return [Item.from_row(row) for row in rows]
    
    @staticmethod
    def add_tag(item_id: int, tag_id: int):
        """Add a tag to an item."""
        db = get_db()
        try:
            db.insert(
                "INSERT OR IGNORE INTO item_tags (item_id, tag_id) VALUES (?, ?)",
                (item_id, tag_id)
            )
        except:
            pass  # Ignore duplicate
    
    @staticmethod
    def add_indicator(item_id: int, indicator_id: int, context: str = None):
        """Add an indicator to an item."""
        db = get_db()
        try:
            db.insert(
                "INSERT OR IGNORE INTO item_indicators (item_id, indicator_id, context) VALUES (?, ?, ?)",
                (item_id, indicator_id, context)
            )
        except:
            pass  # Ignore duplicate
    
    @staticmethod
    def count_by_run(run_id: int) -> int:
        """Count items for a run."""
        db = get_db()
        row = db.execute_one("SELECT COUNT(*) as count FROM items WHERE run_id = ?", (run_id,))
        return row["count"] if row else 0


class IndicatorRepository:
    """Repository for Indicator operations."""
    
    @staticmethod
    def get_or_create(indicator: Indicator) -> int:
        """Get indicator ID or create if not exists."""
        db = get_db()
        
        # Check if exists
        row = db.execute_one(
            "SELECT id FROM indicators WHERE type = ? AND value = ?",
            (indicator.type, indicator.value)
        )
        
        if row:
            # Update last_seen_at
            db.update(
                "UPDATE indicators SET last_seen_at = CURRENT_TIMESTAMP WHERE id = ?",
                (row["id"],)
            )
            return row["id"]
        
        # Create new
        return db.insert(
            """INSERT INTO indicators (type, value, normalized_value, confidence, metadata_json)
               VALUES (?, ?, ?, ?, ?)""",
            (indicator.type, indicator.value, indicator.normalized_value,
             indicator.confidence, indicator.metadata_json)
        )
    
    @staticmethod
    def get_by_id(indicator_id: int, include_items: bool = False) -> Optional[Indicator]:
        """Get an indicator by ID."""
        db = get_db()
        row = db.execute_one("SELECT * FROM indicators WHERE id = ?", (indicator_id,))
        if not row:
            return None
        
        indicator = Indicator.from_row(row)
        
        if include_items:
            item_rows = db.execute(
                """SELECT i.* FROM items i
                   JOIN item_indicators ii ON i.id = ii.item_id
                   WHERE ii.indicator_id = ?""",
                (indicator_id,)
            )
            indicator.items = [Item.from_row(r) for r in item_rows]
        
        return indicator
    
    @staticmethod
    def list_indicators(ind_type: str = None, value: str = None,
                        since: str = None, until: str = None,
                        limit: int = 50, offset: int = 0) -> List[Indicator]:
        """List indicators with optional filters."""
        db = get_db()
        conditions = []
        params = []
        
        if ind_type:
            conditions.append("type = ?")
            params.append(ind_type)
        if value:
            conditions.append("value LIKE ?")
            params.append(f"%{value}%")
        if since:
            conditions.append("first_seen_at >= ?")
            params.append(since)
        if until:
            conditions.append("first_seen_at <= ?")
            params.append(until)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""SELECT * FROM indicators WHERE {where_clause}
                   ORDER BY last_seen_at DESC NULLS LAST
                   LIMIT ? OFFSET ?"""
        params.extend([limit, offset])
        
        rows = db.execute(query, tuple(params))
        return [Indicator.from_row(row) for row in rows]


class TagRepository:
    """Repository for Tag operations."""
    
    @staticmethod
    def get_or_create(name: str) -> int:
        """Get tag ID by name or create if not exists."""
        db = get_db()
        row = db.execute_one("SELECT id FROM tags WHERE name = ?", (name,))
        
        if row:
            return row["id"]
        
        return db.insert("INSERT INTO tags (name) VALUES (?)", (name,))
    
    @staticmethod
    def list_all() -> List[Tag]:
        """List all tags."""
        db = get_db()
        rows = db.execute("SELECT * FROM tags ORDER BY name")
        return [Tag.from_row(row) for row in rows]


class ReportRepository:
    """Repository for Report operations."""
    
    @staticmethod
    def create(report: Report) -> int:
        """Create a new report and return its ID."""
        db = get_db()
        return db.insert(
            """INSERT INTO reports 
               (run_id, query, report, summary, stats_json, telegram_chat_id, telegram_message_id, published_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (report.run_id, report.query, report.report, report.summary,
             report.stats_json, report.telegram_chat_id, report.telegram_message_id,
             report.published_at)
        )
    
    @staticmethod
    def get_by_id(report_id: int) -> Optional[Report]:
        """Get a report by ID."""
        db = get_db()
        row = db.execute_one("SELECT * FROM reports WHERE id = ?", (report_id,))
        return Report.from_row(row)
    
    @staticmethod
    def get_by_run_id(run_id: int) -> Optional[Report]:
        """Get report for a run."""
        db = get_db()
        row = db.execute_one("SELECT * FROM reports WHERE run_id = ?", (run_id,))
        return Report.from_row(row)
    
    @staticmethod
    def list_reports(limit: int = 50, offset: int = 0) -> List[Report]:
        """List reports."""
        db = get_db()
        rows = db.execute(
            "SELECT * FROM reports ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        return [Report.from_row(row) for row in rows]
    
    @staticmethod
    def update_telegram_info(report_id: int, chat_id: str, message_id: str):
        """Update Telegram publish info."""
        db = get_db()
        db.update(
            """UPDATE reports SET telegram_chat_id = ?, telegram_message_id = ?, 
               published_at = CURRENT_TIMESTAMP WHERE id = ?""",
            (chat_id, message_id, report_id)
        )


class AgentLogRepository:
    """Repository for agent execution logs."""
    
    @staticmethod
    def create(run_id: int, agent_name: str, action: str, 
               input_data: Dict = None) -> int:
        """Create a log entry."""
        db = get_db()
        return db.insert(
            """INSERT INTO agent_logs (run_id, agent_name, action, input_data, status)
               VALUES (?, ?, ?, ?, 'started')""",
            (run_id, agent_name, action, json.dumps(input_data) if input_data else None)
        )
    
    @staticmethod
    def complete(log_id: int, output_data: Dict = None, error: str = None):
        """Mark a log entry as complete."""
        db = get_db()
        status = "failed" if error else "completed"
        db.update(
            """UPDATE agent_logs SET status = ?, output_data = ?, error_message = ?,
               finished_at = CURRENT_TIMESTAMP WHERE id = ?""",
            (status, json.dumps(output_data) if output_data else None, error, log_id)
        )


class TraceRepository:
    """
    Repository for detailed execution traces.
    Provides full traceability of tool calls, agent decisions, and evidence.
    """
    
    @staticmethod
    def create(trace: "Trace") -> int:
        """Create a new trace and return its ID."""
        from db.models import Trace
        db = get_db()
        
        # Get next sequence number for this run
        if trace.run_id:
            row = db.execute_one(
                "SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_seq FROM traces WHERE run_id = ?",
                (trace.run_id,)
            )
            trace.sequence_number = row["next_seq"] if row else 1
        
        return db.insert(
            """INSERT INTO traces 
               (run_id, parent_trace_id, sequence_number, trace_type, agent_name, tool_name,
                instruction, reasoning, input_params_json, output_data_json,
                evidence_found_json, evidence_count, confidence_score,
                status, started_at, finished_at, duration_ms,
                error_message, error_type, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (trace.run_id, trace.parent_trace_id, trace.sequence_number,
             trace.trace_type, trace.agent_name, trace.tool_name,
             trace.instruction, trace.reasoning,
             trace.input_params_json, trace.output_data_json,
             trace.evidence_found_json, trace.evidence_count, trace.confidence_score,
             trace.status, trace.started_at, trace.finished_at, trace.duration_ms,
             trace.error_message, trace.error_type, trace.metadata_json)
        )
    
    @staticmethod
    def update(trace: "Trace"):
        """Update an existing trace."""
        from db.models import Trace
        db = get_db()
        db.update(
            """UPDATE traces SET 
               trace_type = ?, agent_name = ?, tool_name = ?,
               instruction = ?, reasoning = ?,
               input_params_json = ?, output_data_json = ?,
               evidence_found_json = ?, evidence_count = ?, confidence_score = ?,
               status = ?, started_at = ?, finished_at = ?, duration_ms = ?,
               error_message = ?, error_type = ?, metadata_json = ?
               WHERE id = ?""",
            (trace.trace_type, trace.agent_name, trace.tool_name,
             trace.instruction, trace.reasoning,
             trace.input_params_json, trace.output_data_json,
             trace.evidence_found_json, trace.evidence_count, trace.confidence_score,
             trace.status, trace.started_at, trace.finished_at, trace.duration_ms,
             trace.error_message, trace.error_type, trace.metadata_json,
             trace.id)
        )
    
    @staticmethod
    def get_by_id(trace_id: int) -> Optional["Trace"]:
        """Get a trace by ID."""
        from db.models import Trace
        db = get_db()
        row = db.execute_one("SELECT * FROM traces WHERE id = ?", (trace_id,))
        return Trace.from_row(row)
    
    @staticmethod
    def get_by_run_id(run_id: int, include_full_data: bool = True) -> List["Trace"]:
        """Get all traces for a run, ordered by sequence number."""
        from db.models import Trace
        db = get_db()
        rows = db.execute(
            "SELECT * FROM traces WHERE run_id = ? ORDER BY sequence_number ASC",
            (run_id,)
        )
        return [Trace.from_row(row) for row in rows]
    
    @staticmethod
    def get_by_agent(run_id: int, agent_name: str) -> List["Trace"]:
        """Get all traces for a specific agent in a run."""
        from db.models import Trace
        db = get_db()
        rows = db.execute(
            """SELECT * FROM traces 
               WHERE run_id = ? AND agent_name = ? 
               ORDER BY sequence_number ASC""",
            (run_id, agent_name)
        )
        return [Trace.from_row(row) for row in rows]
    
    @staticmethod
    def get_by_tool(run_id: int, tool_name: str) -> List["Trace"]:
        """Get all traces for a specific tool in a run."""
        from db.models import Trace
        db = get_db()
        rows = db.execute(
            """SELECT * FROM traces 
               WHERE run_id = ? AND tool_name = ? 
               ORDER BY sequence_number ASC""",
            (run_id, tool_name)
        )
        return [Trace.from_row(row) for row in rows]
    
    @staticmethod
    def get_children(parent_trace_id: int) -> List["Trace"]:
        """Get child traces of a parent trace."""
        from db.models import Trace
        db = get_db()
        rows = db.execute(
            "SELECT * FROM traces WHERE parent_trace_id = ? ORDER BY sequence_number ASC",
            (parent_trace_id,)
        )
        return [Trace.from_row(row) for row in rows]
    
    @staticmethod
    def get_evidence_summary(run_id: int) -> Dict[str, Any]:
        """Get summary of all evidence found in a run."""
        db = get_db()
        
        # Total traces and stats
        stats = db.execute_one(
            """SELECT 
               COUNT(*) as total_traces,
               SUM(evidence_count) as total_evidence,
               AVG(confidence_score) as avg_confidence,
               SUM(duration_ms) as total_duration_ms,
               COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
               COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
               FROM traces WHERE run_id = ?""",
            (run_id,)
        )
        
        # Traces by agent
        agent_rows = db.execute(
            """SELECT agent_name, 
               COUNT(*) as trace_count,
               SUM(evidence_count) as evidence_count,
               AVG(confidence_score) as avg_confidence
               FROM traces WHERE run_id = ? AND agent_name IS NOT NULL
               GROUP BY agent_name""",
            (run_id,)
        )
        
        # Traces by tool
        tool_rows = db.execute(
            """SELECT tool_name, 
               COUNT(*) as trace_count,
               SUM(evidence_count) as evidence_count,
               AVG(duration_ms) as avg_duration_ms
               FROM traces WHERE run_id = ? AND tool_name IS NOT NULL
               GROUP BY tool_name""",
            (run_id,)
        )
        
        return {
            "total_traces": stats["total_traces"] if stats else 0,
            "total_evidence": stats["total_evidence"] if stats else 0,
            "avg_confidence": stats["avg_confidence"] if stats else None,
            "total_duration_ms": stats["total_duration_ms"] if stats else 0,
            "completed_traces": stats["completed"] if stats else 0,
            "failed_traces": stats["failed"] if stats else 0,
            "by_agent": [
                {
                    "agent_name": r["agent_name"],
                    "trace_count": r["trace_count"],
                    "evidence_count": r["evidence_count"],
                    "avg_confidence": r["avg_confidence"]
                } for r in agent_rows
            ],
            "by_tool": [
                {
                    "tool_name": r["tool_name"],
                    "trace_count": r["trace_count"],
                    "evidence_count": r["evidence_count"],
                    "avg_duration_ms": r["avg_duration_ms"]
                } for r in tool_rows
            ]
        }
    
    @staticmethod
    def start_trace(run_id: int, trace_type: str, agent_name: str = None,
                    tool_name: str = None, instruction: str = None,
                    input_params: Dict = None, parent_trace_id: int = None) -> int:
        """Helper to create and start a new trace."""
        from db.models import Trace, TraceStatus
        from datetime import datetime
        
        trace = Trace(
            run_id=run_id,
            parent_trace_id=parent_trace_id,
            trace_type=trace_type,
            agent_name=agent_name,
            tool_name=tool_name,
            instruction=instruction,
            status=TraceStatus.RUNNING.value,
            started_at=datetime.utcnow().isoformat()
        )
        if input_params:
            trace.set_input_params(input_params)
        
        trace_id = TraceRepository.create(trace)
        return trace_id
    
    @staticmethod
    def complete_trace(trace_id: int, output: Any = None, 
                       evidence: List[Dict] = None, 
                       confidence: float = None,
                       reasoning: str = None):
        """Helper to complete an existing trace."""
        from db.models import Trace
        trace = TraceRepository.get_by_id(trace_id)
        if trace:
            if reasoning:
                trace.reasoning = reasoning
            trace.complete(output=output, evidence=evidence, confidence=confidence)
            TraceRepository.update(trace)
    
    @staticmethod
    def fail_trace(trace_id: int, error_message: str, error_type: str = None):
        """Helper to mark a trace as failed."""
        from db.models import Trace
        trace = TraceRepository.get_by_id(trace_id)
        if trace:
            trace.fail(error_message, error_type)
            TraceRepository.update(trace)
    
    @staticmethod
    def count_by_run(run_id: int) -> int:
        """Count traces for a run."""
        db = get_db()
        row = db.execute_one("SELECT COUNT(*) as count FROM traces WHERE run_id = ?", (run_id,))
        return row["count"] if row else 0
