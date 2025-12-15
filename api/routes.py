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


def error_response(message: str, status_code: int = 400):
    """Create error response."""
    return jsonify({"error": message}), status_code


async def publish_to_telegram(report_text: str, topic: str, run_id: int) -> dict:
    """
    Publish investigation report to Telegram via MCP service.
    
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
    
    telegram_mcp_url = os.getenv("TELEGRAM_MCP_URL", "http://localhost:5001")
    
    # Format the message
    # Telegram has a 4096 character limit per message
    header = f"🔍 **OSINT Investigation Report**\n"
    header += f"📋 Topic: {topic}\n"
    header += f"🆔 Run ID: {run_id}\n"
    header += f"{'─' * 30}\n\n"
    
    # Truncate if too long (leave room for header)
    max_content = 4000 - len(header)
    if len(report_text) > max_content:
        report_text = report_text[:max_content - 100] + "\n\n... [Report truncated, see full version in web UI]"
    
    message = header + report_text
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{telegram_mcp_url}/send",
                json={
                    "name": target_dialog,
                    "text": message
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Report published to Telegram: {target_dialog}")
                return {"published": True, "dialog": target_dialog, "result": result}
            else:
                error_msg = response.text
                logger.error(f"Telegram publish failed: {response.status_code} - {error_msg}")
                return {"published": False, "reason": f"HTTP {response.status_code}: {error_msg}"}
                
    except httpx.TimeoutException:
        logger.error("Telegram MCP service timeout")
        return {"published": False, "reason": "Telegram MCP service timeout"}
    except httpx.ConnectError:
        logger.error("Cannot connect to Telegram MCP service")
        return {"published": False, "reason": "Cannot connect to Telegram MCP service"}
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
    
    # Create run record in database first
    run_id = RunRepository.create(
        query=query,
        initiated_by="api",
        limit_requested=limit,
        since=since,
        scope=scope
    )
    
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
            depth=depth,
            run_id=run_id
        )
        
        # Extract report text
        report_text = result.get("report", "")
        
        # Store the report
        report_obj = Report(
            run_id=run_id,
            query=query,
            report=report_text,
            summary=f"Investigation: {query[:100]}"
        )
        report_id = ReportRepository.create(report_obj)
        
        # Publish to Telegram if enabled
        telegram_result = {"published": False, "reason": "Publishing disabled"}
        if publish_telegram and report_text:
            logger.info(f"Publishing report to Telegram for run {run_id}...")
            telegram_result = await publish_to_telegram(
                report_text=report_text,
                topic=query,
                run_id=run_id
            )
            logger.info(f"Telegram publish result: {telegram_result}")
        
        # Update run status to completed
        stats = {
            "depth": depth,
            "agents_used": result.get("metadata", {}).get("agents_used", "auto"),
            "telegram_published": telegram_result.get("published", False),
        }
        RunRepository.update_status(run_id, "completed", stats=stats)
        
        # Return response compatible with frontend expectations
        return success_response({
            "run_id": run_id,
            "items_count": 0,  # Agent-based investigation doesn't create items
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
    """List all registered OSINT agents and their status (legacy + LangChain)."""
    from agents.osint_base import AgentRegistry
    from agents.langchain_base import LangChainAgentRegistry
    
    agents = []
    
    # LangChain agents first (preferred)
    for name, agent in LangChainAgentRegistry.get_all().items():
        available, msg = agent.is_available()
        agents.append({
            "name": name,
            "available": available,
            "message": msg,
            "type": "langchain",
            "capabilities": agent.capabilities.to_dict()
        })
    
    # Legacy agents
    for name, agent in AgentRegistry.get_all().items():
        available, msg = agent.is_available()
        agents.append({
            "name": name,
            "available": available,
            "message": msg,
            "type": "legacy",
            "capabilities": agent.capabilities.to_dict()
        })
    
    return success_response({
        "agents": agents,
        "total": len(agents),
        "available": sum(1 for a in agents if a["available"]),
        "langchain_count": sum(1 for a in agents if a.get("type") == "langchain"),
        "legacy_count": sum(1 for a in agents if a.get("type") == "legacy")
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
