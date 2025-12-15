# =============================================================================
# OSINT News Aggregator - Database Package
# =============================================================================
"""
Database layer package.
"""

from db.sqlite import init_db, get_db, Database
from db.models import (
    Run, RunStatus, Item, ItemType, Indicator, IndicatorType,
    Tag, Source, SourceKind, Report, OsintResult, OsintReport,
    OsintTask, TaskPlan, Trace, TraceType, TraceStatus
)
from db.repository import (
    RunRepository, SourceRepository, ItemRepository,
    IndicatorRepository, TagRepository, ReportRepository,
    AgentLogRepository, TraceRepository
)

__all__ = [
    # Database
    "init_db", "get_db", "Database",
    # Models
    "Run", "RunStatus", "Item", "ItemType", "Indicator", "IndicatorType",
    "Tag", "Source", "SourceKind", "Report", "OsintResult", "OsintReport",
    "OsintTask", "TaskPlan", "Trace", "TraceType", "TraceStatus",
    # Repositories
    "RunRepository", "SourceRepository", "ItemRepository",
    "IndicatorRepository", "TagRepository", "ReportRepository",
    "AgentLogRepository", "TraceRepository"
]
