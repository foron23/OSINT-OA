# =============================================================================
# OSINT Agentic Operations - API Routes
# =============================================================================
"""
Flask API routes for OSINT investigations, evidence access, and agent control.
"""

import asyncio
import json
import logging
import os
from flask import Blueprint, request, jsonify
from functools import wraps

import httpx

from db import (
    RunRepository, ItemRepository, IndicatorRepository,
    ReportRepository, TagRepository, SourceRepository, Report,
    TraceRepository, Trace
)
from agents.control import ControlAgent
from config.settings import settings

logger = logging.getLogger(__name__)

# Create blueprints
api = Blueprint('api', __name__, url_prefix='/api')


# =============================================================================
# Helpers
# =============================================================================

def async_route(f):
    """Decorator to run async functions in Flask."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper


def get_pagination():
    """Get pagination parameters from request."""
    try:
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = max(int(request.args.get('offset', 0)), 0)
    except (ValueError, TypeError):
        limit = 50
        offset = 0
    return limit, offset


def error_response(message: str, status_code: int = 400, error_type: str = None):
    """Create error response with detailed information."""
    response = {"error": message}
    if error_type:
        response["error_type"] = error_type
    return jsonify(response), status_code


def handle_database_error(e: Exception):
    """Handle database errors with user-friendly messages."""
    error_str = str(e).lower()
    
    if "readonly database" in error_str:
        return error_response(
            "Database is read-only. Please check volume permissions.",
            500,
            "database_readonly"
        )
    elif "no such table" in error_str:
        return error_response(
            "Database not initialized. Please restart the application.",
            500,
            "database_not_initialized"
        )
    elif "database is locked" in error_str:
        return error_response(
            "Database is busy. Please try again in a moment.",
            503,
            "database_locked"
        )
    else:
        return error_response(
            f"Database error: {e}",
            500,
            "database_error"
        )


async def publish_to_telegram(report_text: str, topic: str, run_id: int) -> dict:
    """
    Publish investigation report to Telegram via Telethon.
    
    Args:
        report_text: The report content to publish
        topic: Investigation topic (for message header)
        run_id: Run ID for reference
        
    Returns:
        Dict with success status and details
    """
    # Check if Telegram publishing is enabled
    target_dialog = settings.TELEGRAM_TARGET_DIALOG
    if not target_dialog:
        logger.warning("TELEGRAM_TARGET_DIALOG not configured, skipping publish")
        return {"published": False, "reason": "TELEGRAM_TARGET_DIALOG not configured"}
    
    try:
        from integrations.telegram.telethon_client import TelethonReportPublisher
        
        publisher = TelethonReportPublisher(target_dialog=target_dialog)
        
        result = await publisher.publish_report(
            report_markdown=report_text,
            query=topic,
            run_id=run_id,
            dialog_name=target_dialog
        )
        
        await publisher.close()
        
        if result.get("success"):
            logger.info(f"Report published to Telegram: {target_dialog}")
            return {"published": True, "dialog": target_dialog, "result": result}
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Telegram publish failed: {error_msg}")
            return {"published": False, "reason": error_msg}
            
    except ImportError as e:
        logger.error(f"Telethon not available: {e}")
        return {"published": False, "reason": "Telethon not installed"}
    except Exception as e:
        logger.error(f"Telegram publish error: {e}")
        return {"published": False, "reason": str(e)}


def success_response(data, status_code: int = 200):
    """Create success response."""
    return jsonify(data), status_code


# =============================================================================
# Runs (Investigations) Endpoints
# =============================================================================

@api.route('/runs', methods=['GET'])
def list_runs():
    """
    List investigation runs with optional filters.
    
    Query params:
        q: Search in query text
        status: Filter by status (started|completed|failed|partial)
        since: Filter by start date (ISO-8601)
        until: Filter by end date (ISO-8601)
        limit: Max results (default 50, max 100)
        offset: Pagination offset
    """
    q = request.args.get('q')
    status = request.args.get('status')
    since = request.args.get('since')
    until = request.args.get('until')
    limit, offset = get_pagination()
    
    runs = RunRepository.list_runs(
        q=q, status=status, since=since, until=until,
        limit=limit, offset=offset
    )
    
    return success_response({
        "runs": [r.to_dict() for r in runs],
        "count": len(runs),
        "limit": limit,
        "offset": offset
    })


@api.route('/runs/<int:run_id>', methods=['GET'])
def get_run(run_id):
    """
    Get a single run by ID.
    
    Includes:
        - Run details
        - Item count
        - Associated report (if exists)
    """
    run = RunRepository.get_by_id(run_id)
    if not run:
        return error_response("Run not found", 404)
    
    # Get additional info
    item_count = ItemRepository.count_by_run(run_id)
    report = ReportRepository.get_by_run_id(run_id)
    
    result = run.to_dict()
    result["items_count"] = item_count
    result["report"] = report.to_dict() if report else None
    
    return success_response(result)


@api.route('/runs/<int:run_id>', methods=['DELETE'])
def delete_run(run_id):
    """
    Delete a run and all associated data.
    
    Cascade deletes:
        - Items associated with this run
        - Reports associated with this run
        - Agent logs
    """
    run = RunRepository.get_by_id(run_id)
    if not run:
        return error_response("Run not found", 404)
    
    success = RunRepository.delete(run_id)
    
    if success:
        return success_response({"message": f"Run {run_id} deleted successfully"})
    else:
        return error_response("Failed to delete run", 500)


@api.route('/runs/<int:run_id>/continue', methods=['POST'])
@async_route
async def continue_investigation(run_id):
    """
    Continue a previous investigation with new instructions.
    
    Allows resuming an investigation by providing:
    - New instructions or focus areas
    - Specific agents to use
    - Selected evidence/IOCs from the previous investigation to focus on
    
    Body:
        new_instructions: Additional instructions or focus areas (optional)
        agents: List of specific agent names to use (optional)
        selected_iocs: List of IOC values to focus on (optional)
        selected_evidence: List of evidence items to include as context (optional)
        depth: Investigation depth (quick/standard/deep, default: standard)
        publish_telegram: Whether to publish to Telegram (default True)
    
    Returns:
        New run ID with continued investigation results
    """
    # Get original run
    original_run = RunRepository.get_by_id(run_id)
    if not original_run:
        return error_response("Run not found", 404)
    
    data = request.get_json() or {}
    
    new_instructions = data.get('new_instructions', '')
    selected_agents = data.get('agents')
    selected_iocs = data.get('selected_iocs', [])
    selected_evidence = data.get('selected_evidence', [])
    depth = data.get('depth', 'standard')
    publish_telegram = data.get('publish_telegram', True)
    
    # Validate agents if provided
    if selected_agents:
        if not isinstance(selected_agents, list):
            return error_response("'agents' must be a list of agent names")
        from agents.registry import AgentRegistry
        available_agents = AgentRegistry.list_all()
        invalid_agents = [a for a in selected_agents if a not in available_agents]
        if invalid_agents:
            return error_response(f"Invalid agents: {invalid_agents}. Available: {available_agents}")
    
    # Get previous report for context
    previous_report = ReportRepository.get_by_run_id(run_id)
    previous_findings = previous_report.report if previous_report else ""
    
    # Create new run record
    try:
        new_run_id = RunRepository.create(
            query=f"Continue: {original_run.query}",
            initiated_by="api",
            limit_requested=30 if depth == "standard" else (10 if depth == "quick" else 50),
            scope=original_run.scope if hasattr(original_run, 'scope') else None
        )
    except Exception as e:
        logger.error(f"Failed to create run record: {e}")
        return handle_database_error(e)
    
    # Initialize control agent
    control_agent = ControlAgent()
    
    try:
        # Build continuation context
        continue_from = {
            "previous_findings": previous_findings,
            "previous_iocs": selected_iocs,
            "selected_evidence": selected_evidence,
            "new_instructions": new_instructions,
            "original_run_id": run_id,
        }
        
        # Run continued investigation
        result = control_agent.investigate(
            topic=original_run.query,
            agents=selected_agents,
            depth=depth,
            run_id=new_run_id,
            continue_from=continue_from
        )
        
        # Extract report text
        report_text = result.get("report", "")
        investigation_status = result.get("status", "completed")
        
        # Store the report
        report_obj = Report(
            run_id=new_run_id,
            query=f"Continue: {original_run.query}",
            report=report_text,
            summary=f"Continued investigation from run #{run_id}: {original_run.query[:80]}"
        )
        report_id = ReportRepository.create(report_obj)
        
        # Publish to Telegram if enabled
        telegram_result = {"published": False, "reason": "Publishing disabled"}
        if publish_telegram and report_text and investigation_status != "failed":
            logger.info(f"Publishing continued report to Telegram for run {new_run_id}...")
            telegram_result = await publish_to_telegram(
                report_text=report_text,
                topic=f"Continue: {original_run.query}",
                run_id=new_run_id
            )
            logger.info(f"Telegram publish result: {telegram_result}")
        
        # Update run status
        stats = {
            "depth": depth,
            "agents_used": selected_agents or result.get("metadata", {}).get("agents_used", "auto"),
            "telegram_published": telegram_result.get("published", False),
            "continued_from": run_id,
            "agents_succeeded": result.get("metadata", {}).get("agents_succeeded", 0),
            "agents_failed": result.get("metadata", {}).get("agents_failed", 0),
        }
        RunRepository.update_status(new_run_id, investigation_status, stats=stats)
        
        return success_response({
            "run_id": new_run_id,
            "continued_from": run_id,
            "status": investigation_status,
            "partial": result.get("partial", False),
            "report": {
                "id": report_id,
                "telegram_published": telegram_result.get("published", False),
                "telegram_details": telegram_result,
            },
            "investigation": result
        })
        
    except Exception as e:
        RunRepository.update_status(new_run_id, "failed", stats={"error": str(e)})
        return error_response(f"Continuation failed: {e}", 500)


# =============================================================================
# Traces Endpoints (Execution Traceability)
# =============================================================================

@api.route('/runs/<int:run_id>/traces', methods=['GET'])
def get_run_traces(run_id):
    """
    Get all execution traces for a run.
    
    Returns a timeline of all tool calls, agent actions, and decisions
    made during the investigation, including evidence found at each step.
    
    Query params:
        agent: Filter by agent name
        tool: Filter by tool name
        include_data: Include full input/output data (default: true)
    """
    run = RunRepository.get_by_id(run_id)
    if not run:
        return error_response("Run not found", 404)
    
    agent_filter = request.args.get('agent')
    tool_filter = request.args.get('tool')
    include_data = request.args.get('include_data', 'true').lower() == 'true'
    
    if agent_filter:
        traces = TraceRepository.get_by_agent(run_id, agent_filter)
    elif tool_filter:
        traces = TraceRepository.get_by_tool(run_id, tool_filter)
    else:
        traces = TraceRepository.get_by_run_id(run_id)
    
    return success_response({
        "run_id": run_id,
        "traces": [t.to_dict(include_full_data=include_data) for t in traces],
        "count": len(traces)
    })


@api.route('/runs/<int:run_id>/traces/summary', methods=['GET'])
def get_run_traces_summary(run_id):
    """
    Get a summary of execution traces for a run.
    
    Returns aggregated statistics about tool usage, agent activity,
    evidence collected, and timing information.
    """
    run = RunRepository.get_by_id(run_id)
    if not run:
        return error_response("Run not found", 404)
    
    summary = TraceRepository.get_evidence_summary(run_id)
    summary["run_id"] = run_id
    summary["run_status"] = run.status
    summary["run_query"] = run.query
    
    return success_response(summary)


@api.route('/runs/<int:run_id>/traces/<int:trace_id>', methods=['GET'])
def get_trace_detail(run_id, trace_id):
    """
    Get detailed information about a specific trace.
    
    Includes:
        - Full input parameters
        - Complete output data
        - Evidence found
        - Child traces (if any)
        - Error details (if failed)
    """
    trace = TraceRepository.get_by_id(trace_id)
    if not trace or trace.run_id != run_id:
        return error_response("Trace not found", 404)
    
    result = trace.to_dict(include_full_data=True)
    
    # Get child traces if this is a parent
    children = TraceRepository.get_children(trace_id)
    if children:
        result["children"] = [c.to_dict(include_full_data=False) for c in children]
    
    return success_response(result)


@api.route('/runs/<int:run_id>/traces/<int:trace_id>/evidence', methods=['GET'])
def get_trace_evidence(run_id, trace_id):
    """
    Get only the evidence found in a specific trace.
    
    Returns a focused view of the evidence/findings from this execution step.
    """
    trace = TraceRepository.get_by_id(trace_id)
    if not trace or trace.run_id != run_id:
        return error_response("Trace not found", 404)
    
    evidence = []
    if trace.evidence_found_json:
        try:
            evidence = json.loads(trace.evidence_found_json)
        except:
            pass
    
    return success_response({
        "trace_id": trace_id,
        "tool_name": trace.tool_name,
        "agent_name": trace.agent_name,
        "evidence_count": trace.evidence_count,
        "confidence_score": trace.confidence_score,
        "evidence": evidence
    })


@api.route('/traces/recent', methods=['GET'])
def get_recent_traces():
    """
    Get recent traces across all runs.
    
    Query params:
        limit: Max results (default 50, max 100)
        status: Filter by status (pending|running|completed|failed)
    """
    from db import get_db
    limit, _ = get_pagination()
    status_filter = request.args.get('status')
    
    db = get_db()
    if status_filter:
        rows = db.execute(
            """SELECT t.*, r.query as run_query 
               FROM traces t 
               JOIN runs r ON t.run_id = r.id
               WHERE t.status = ?
               ORDER BY t.created_at DESC LIMIT ?""",
            (status_filter, limit)
        )
    else:
        rows = db.execute(
            """SELECT t.*, r.query as run_query 
               FROM traces t 
               JOIN runs r ON t.run_id = r.id
               ORDER BY t.created_at DESC LIMIT ?""",
            (limit,)
        )
    
    traces = []
    for row in rows:
        trace = Trace.from_row(row)
        trace_dict = trace.to_dict(include_full_data=False)
        trace_dict["run_query"] = row["run_query"]
        traces.append(trace_dict)
    
    return success_response({
        "traces": traces,
        "count": len(traces)
    })


# =============================================================================
# Items Endpoints
# =============================================================================

@api.route('/items', methods=['GET'])
def list_items():
    """
    List OSINT items with optional filters.
    
    Query params:
        q: Search in title/summary
        source: Filter by source name
        tag: Filter by tag
        indicator_type: Filter by indicator type
        indicator_value: Filter by indicator value
        run_id: Filter by run ID
        since: Filter by published date (ISO-8601)
        until: Filter by published date (ISO-8601)
        limit: Max results (default 50, max 100)
        offset: Pagination offset
    """
    q = request.args.get('q')
    source = request.args.get('source')
    tag = request.args.get('tag')
    indicator_type = request.args.get('indicator_type')
    indicator_value = request.args.get('indicator_value')
    run_id = request.args.get('run_id', type=int)
    since = request.args.get('since')
    until = request.args.get('until')
    limit, offset = get_pagination()
    
    items = ItemRepository.list_items(
        q=q, source=source, tag=tag,
        indicator_type=indicator_type, indicator_value=indicator_value,
        run_id=run_id, since=since, until=until,
        limit=limit, offset=offset
    )
    
    return success_response({
        "items": [i.to_dict(include_relations=False) for i in items],
        "count": len(items),
        "limit": limit,
        "offset": offset
    })


@api.route('/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    """
    Get a single item by ID.
    
    Includes:
        - Full item details
        - Associated tags
        - Associated indicators
        - Source info
    """
    item = ItemRepository.get_by_id(item_id, include_relations=True)
    if not item:
        return error_response("Item not found", 404)
    
    return success_response(item.to_dict(include_relations=True))


@api.route('/items', methods=['POST'])
def create_item():
    """
    Create a new item (for testing/manual insertion).
    
    Body:
        title: Item title (required)
        summary: Item summary (required)
        url: Item URL (required)
        source_name: Source name (default: "Manual")
        published_at: Publication date
        tags: List of tag names
        indicators: List of indicator dicts [{type, value, confidence}]
    """
    data = request.get_json()
    if not data:
        return error_response("JSON body required")
    
    # Validate required fields
    required = ['title', 'summary', 'url']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error_response(f"Missing required fields: {', '.join(missing)}")
    
    from db.models import OsintResult
    
    result = OsintResult(
        title=data['title'],
        summary=data['summary'],
        url=data['url'],
        source_name=data.get('source_name', 'Manual'),
        published_at=data.get('published_at'),
        tags=data.get('tags', []),
        indicators=data.get('indicators', [])
    )
    
    try:
        item_id = ItemRepository.create_from_osint_result(result, run_id=None)
        return success_response({"id": item_id, "message": "Item created"}, 201)
    except Exception as e:
        return error_response(f"Failed to create item: {e}", 500)


# =============================================================================
# Indicators Endpoints
# =============================================================================

@api.route('/indicators', methods=['GET'])
def list_indicators():
    """
    List indicators/IOCs with optional filters.
    
    Query params:
        type: Filter by type (ip|domain|url|hash|email|cve|handle|other)
        value: Search in value
        since: Filter by first_seen date
        until: Filter by first_seen date
        limit: Max results (default 50, max 100)
        offset: Pagination offset
    """
    ind_type = request.args.get('type')
    value = request.args.get('value')
    since = request.args.get('since')
    until = request.args.get('until')
    limit, offset = get_pagination()
    
    indicators = IndicatorRepository.list_indicators(
        ind_type=ind_type, value=value,
        since=since, until=until,
        limit=limit, offset=offset
    )
    
    return success_response({
        "indicators": [i.to_dict() for i in indicators],
        "count": len(indicators),
        "limit": limit,
        "offset": offset
    })


@api.route('/indicators/<int:indicator_id>', methods=['GET'])
def get_indicator(indicator_id):
    """
    Get a single indicator by ID.
    
    Includes related items.
    """
    indicator = IndicatorRepository.get_by_id(indicator_id, include_items=True)
    if not indicator:
        return error_response("Indicator not found", 404)
    
    return success_response(indicator.to_dict(include_items=True))


# =============================================================================
# Reports Endpoints
# =============================================================================

@api.route('/reports', methods=['GET'])
def list_reports():
    """
    List generated reports.
    
    Query params:
        limit: Max results (default 50)
        offset: Pagination offset
    """
    limit, offset = get_pagination()
    
    reports = ReportRepository.list_reports(limit=limit, offset=offset)
    
    return success_response({
        "reports": [r.to_dict() for r in reports],
        "count": len(reports),
        "limit": limit,
        "offset": offset
    })


@api.route('/reports/<int:report_id>', methods=['GET'])
def get_report(report_id):
    """Get a single report by ID."""
    report = ReportRepository.get_by_id(report_id)
    if not report:
        return error_response("Report not found", 404)
    
    return success_response(report.to_dict())


# =============================================================================
# Collection Endpoint (Agent Integration)
# =============================================================================

@api.route('/collect', methods=['POST'])
@async_route
async def collect():
    """
    Trigger an OSINT collection through the Control Agent.
    
    Body:
        query: Search query/objective (required)
        limit: Maximum results to collect (default 20)
        since: Only collect from this date (ISO-8601)
        scope: Allowed scope for the investigation
        publish_telegram: Whether to publish to Telegram (default True)
        agents: List of specific agent names to use (optional, default: auto)
    
    Returns:
        Run ID, items collected, report info, and Telegram status
    """
    data = request.get_json()
    if not data:
        return error_response("JSON body required")
    
    query = data.get('query')
    if not query:
        return error_response("'query' is required")
    
    limit = data.get('limit', 20)
    since = data.get('since')
    scope = data.get('scope')
    publish_telegram = data.get('publish_telegram', True)
    selected_agents = data.get('agents')  # New: optional list of agents to use
    
    # Validate selected agents if provided
    if selected_agents:
        if not isinstance(selected_agents, list):
            return error_response("'agents' must be a list of agent names")
        # Validate agent names
        from agents.registry import AgentRegistry
        available_agents = AgentRegistry.list_all()
        invalid_agents = [a for a in selected_agents if a not in available_agents]
        if invalid_agents:
            return error_response(f"Invalid agents: {invalid_agents}. Available: {available_agents}")
    
    # Create run record in database first
    try:
        run_id = RunRepository.create(
            query=query,
            initiated_by="api",
            limit_requested=limit,
            since=since,
            scope=scope
        )
    except Exception as e:
        logger.error(f"Failed to create run record: {e}")
        return handle_database_error(e)
    
    # Initialize control agent
    control_agent = ControlAgent()
    
    try:
        # Map limit to depth
        if limit <= 10:
            depth = "quick"
        elif limit <= 30:
            depth = "standard"
        else:
            depth = "deep"
        
        # Run investigation using the correct method with run_id for tracing
        result = control_agent.investigate(
            topic=query,
            agents=selected_agents,  # Pass selected agents
            depth=depth,
            run_id=run_id
        )
        
        # Extract report text
        report_text = result.get("report", "")
        investigation_status = result.get("status", "completed")
        
        # Store the report
        report_obj = Report(
            run_id=run_id,
            query=query,
            report=report_text,
            summary=f"Investigation: {query[:100]}"
        )
        report_id = ReportRepository.create(report_obj)
        
        # Publish to Telegram if enabled (skip for failed investigations)
        telegram_result = {"published": False, "reason": "Publishing disabled"}
        if publish_telegram and report_text and investigation_status != "failed":
            logger.info(f"Publishing report to Telegram for run {run_id}...")
            telegram_result = await publish_to_telegram(
                report_text=report_text,
                topic=query,
                run_id=run_id
            )
            logger.info(f"Telegram publish result: {telegram_result}")
        
        # Update run status based on investigation result
        stats = {
            "depth": depth,
            "agents_used": selected_agents or result.get("metadata", {}).get("agents_used", "auto"),
            "telegram_published": telegram_result.get("published", False),
            "agents_succeeded": result.get("metadata", {}).get("agents_succeeded", 0),
            "agents_failed": result.get("metadata", {}).get("agents_failed", 0),
        }
        RunRepository.update_status(run_id, investigation_status, stats=stats)
        
        # Return response compatible with frontend expectations
        return success_response({
            "run_id": run_id,
            "items_count": 0,  # Agent-based investigation doesn't create items
            "status": investigation_status,
            "partial": result.get("partial", False),
            "report": {
                "id": report_id,
                "telegram_published": telegram_result.get("published", False),
                "telegram_details": telegram_result,
            },
            "investigation": result
        })
        
    except Exception as e:
        # Mark run as failed
        RunRepository.update_status(run_id, "failed", stats={"error": str(e)})
        return error_response(f"Collection failed: {e}", 500)


# =============================================================================
# Utility Endpoints
# =============================================================================

@api.route('/sources', methods=['GET'])
def list_sources():
    """List all configured data sources."""
    sources = SourceRepository.list_all()
    return success_response({
        "sources": [s.to_dict() for s in sources]
    })


@api.route('/tags', methods=['GET'])
def list_tags():
    """List all tags."""
    tags = TagRepository.list_all()
    return success_response({
        "tags": [t.to_dict() for t in tags]
    })


@api.route('/agents', methods=['GET'])
def list_agents():
    """List all registered OSINT agents and their status."""
    from agents.registry import AgentRegistry
    
    agents = []
    
    # Get all registered agents
    for name in AgentRegistry.list_all():
        agent = AgentRegistry.get(name)
        if agent:
            available, msg = agent.is_available()
            agents.append({
                "name": name,
                "available": available,
                "message": msg,
                "type": "langchain",
                "capabilities": agent.capabilities.to_dict()
            })
    
    return success_response({
        "agents": agents,
        "total": len(agents),
        "available": sum(1 for a in agents if a["available"]),
    })


@api.route('/health', methods=['GET'])
def health_check():
    """API health check."""
    from config import config
    
    return success_response({
        "status": "ok",
        "version": "1.0.0",
        "database": config.DATABASE_PATH,
        "telegram_configured": bool(config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID)
    })


@api.route('/telegram/status', methods=['GET'])
@async_route
async def telegram_status():
    """
    Check Telegram connectivity status.
    
    Returns detailed information about:
    - Configuration status
    - Session file status
    - Connection status
    - Authenticated user info
    """
    import os
    from pathlib import Path
    
    result = {
        "configured": False,
        "session_exists": False,
        "connected": False,
        "authorized": False,
        "user": None,
        "error": None,
    }
    
    # Check configuration
    app_id = os.getenv("TG_APP_ID") or os.getenv("TELEGRAM_APP_ID")
    api_hash = os.getenv("TG_API_HASH") or os.getenv("TELEGRAM_API_HASH")
    
    if not app_id or not api_hash:
        result["error"] = "Telegram credentials not configured (TG_APP_ID, TG_API_HASH)"
        return success_response(result)
    
    result["configured"] = True
    
    # Check session file
    session_path = os.getenv("TELEGRAM_SESSION_PATH", "/app/data/telegram-session")
    session_file = Path(session_path) / "osint_bot.session"
    
    result["session_path"] = str(session_path)
    result["session_exists"] = session_file.exists()
    
    if not result["session_exists"]:
        result["error"] = "Session file not found. Run: python scripts/setup_telegram.py"
        return success_response(result)
    
    # Try to connect
    try:
        from integrations.telegram.telethon_client import TelethonClient
        client = TelethonClient()
        
        connected = await client.connect()
        result["connected"] = connected
        
        if connected:
            result["authorized"] = True
            me = await client._client.get_me()
            result["user"] = {
                "id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name,
            }
            await client.disconnect()
        else:
            result["error"] = "Session not authorized. Run: python scripts/setup_telegram.py"
    except Exception as e:
        result["error"] = str(e)
    
    return success_response(result)


@api.route('/telegram/test', methods=['POST'])
@async_route
async def telegram_test_message():
    """
    Send a test message to verify Telegram integration.
    
    Request body:
    {
        "chat_id": "optional - defaults to configured TELEGRAM_CHAT_ID",
        "message": "optional - test message content"
    }
    """
    import os
    
    data = request.get_json() or {}
    chat_id = data.get("chat_id") or os.getenv("TELEGRAM_CHAT_ID")
    message = data.get("message", "🔧 OSINT-OA Test Message - Telegram integration is working!")
    
    if not chat_id:
        return error_response("No chat_id provided and TELEGRAM_CHAT_ID not configured", 400)
    
    try:
        from integrations.telegram.telethon_client import TelethonClient
        client = TelethonClient()
        
        connected = await client.connect()
        if not connected:
            return error_response("Could not connect to Telegram. Run setup_telegram.py first", 503)
        
        result = await client.send_message(chat_id, message, parse_mode="html")
        await client.disconnect()
        
        if result.get("success"):
            return success_response({
                "status": "sent",
                "chat_id": chat_id,
                "message_id": result.get("message_id"),
            })
        else:
            return error_response(result.get("error", "Failed to send message"), 500)
    
    except Exception as e:
        logger.exception("Error sending test message")
        return error_response(str(e), 500)
