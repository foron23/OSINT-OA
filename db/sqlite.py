# =============================================================================
# OSINT News Aggregator - Database Layer
# =============================================================================
"""
SQLite database connection and schema initialization.
"""

import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

from config import config

logger = logging.getLogger(__name__)

# =============================================================================
# Database Schema
# =============================================================================

SCHEMA_SQL = """
-- =============================================================================
-- OSINT News Aggregator Database Schema
-- =============================================================================

-- Runs table: tracks collection executions
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    since TEXT,
    until TEXT,
    limit_requested INTEGER,
    status TEXT NOT NULL DEFAULT 'started',  -- started|completed|failed|partial
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    stats_json TEXT,
    scope TEXT,  -- allowed scope for this run
    initiated_by TEXT DEFAULT 'api',  -- audit: who started this
    CONSTRAINT valid_status CHECK (status IN ('started', 'completed', 'failed', 'partial'))
);

-- Sources table: normalized data sources
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    kind TEXT,  -- search|cli|rss|web|api
    base_url TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_kind CHECK (kind IN ('search', 'cli', 'rss', 'web', 'api', 'other'))
);

-- Items table: main evidence/news items
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    source_id INTEGER,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    url TEXT NOT NULL,
    image_url TEXT,
    published_at TEXT,
    item_type TEXT DEFAULT 'article',  -- article|mention|report|other
    language TEXT,
    content_hash TEXT,
    raw_data TEXT,  -- JSON with original data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE SET NULL,
    CONSTRAINT valid_item_type CHECK (item_type IN ('article', 'mention', 'report', 'other'))
);

-- Unique index for deduplication by URL
CREATE UNIQUE INDEX IF NOT EXISTS idx_items_url ON items(url);

-- Index for content hash deduplication
CREATE INDEX IF NOT EXISTS idx_items_content_hash ON items(content_hash);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_items_published_at ON items(published_at);
CREATE INDEX IF NOT EXISTS idx_items_source_id ON items(source_id);
CREATE INDEX IF NOT EXISTS idx_items_run_id ON items(run_id);
CREATE INDEX IF NOT EXISTS idx_items_created_at ON items(created_at);

-- Indicators table: IOCs and artifacts
CREATE TABLE IF NOT EXISTS indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,  -- ip|domain|url|hash|email|cve|handle|other
    value TEXT NOT NULL,
    normalized_value TEXT,
    confidence REAL,  -- 0.0 to 1.0
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP,
    metadata_json TEXT,
    CONSTRAINT valid_type CHECK (type IN ('ip', 'domain', 'url', 'hash', 'email', 'cve', 'handle', 'other'))
);

-- Unique index for indicators
CREATE UNIQUE INDEX IF NOT EXISTS idx_indicators_type_value ON indicators(type, value);

-- Item-Indicators junction table (N:M relationship)
CREATE TABLE IF NOT EXISTS item_indicators (
    item_id INTEGER NOT NULL,
    indicator_id INTEGER NOT NULL,
    context TEXT,  -- where in the item this indicator was found
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (item_id, indicator_id),
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY (indicator_id) REFERENCES indicators(id) ON DELETE CASCADE
);

-- Tags table
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Item-Tags junction table (N:M relationship)
CREATE TABLE IF NOT EXISTS item_tags (
    item_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (item_id, tag_id),
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Reports table: stores generated reports
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    query TEXT NOT NULL,
    report TEXT NOT NULL,  -- Markdown report content
    summary TEXT,
    stats_json TEXT,
    telegram_chat_id TEXT,
    telegram_message_id TEXT,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_run_id ON reports(run_id);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at);

-- Agent executions audit log
CREATE TABLE IF NOT EXISTS agent_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    agent_name TEXT NOT NULL,
    action TEXT NOT NULL,
    input_data TEXT,
    output_data TEXT,
    status TEXT DEFAULT 'started',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_logs_run_id ON agent_logs(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent_name ON agent_logs(agent_name);

-- Traces table: detailed execution traces for investigations
CREATE TABLE IF NOT EXISTS traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    parent_trace_id INTEGER,
    sequence_number INTEGER DEFAULT 0,
    
    -- Execution context
    trace_type TEXT NOT NULL DEFAULT 'tool_call',
    agent_name TEXT,
    tool_name TEXT,
    
    -- Instruction and reasoning
    instruction TEXT,
    reasoning TEXT,
    
    -- Input/Output data (JSON)
    input_params_json TEXT,
    output_data_json TEXT,
    
    -- Evidence tracking
    evidence_found_json TEXT,
    evidence_count INTEGER DEFAULT 0,
    confidence_score REAL,
    
    -- Execution timing
    status TEXT DEFAULT 'pending',
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    duration_ms INTEGER,
    
    -- Error handling
    error_message TEXT,
    error_type TEXT,
    
    -- Metadata
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_trace_id) REFERENCES traces(id) ON DELETE SET NULL,
    CONSTRAINT valid_trace_type CHECK (trace_type IN ('tool_call', 'agent_action', 'llm_reasoning', 'decision', 'error', 'checkpoint')),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped'))
);

CREATE INDEX IF NOT EXISTS idx_traces_run_id ON traces(run_id);
CREATE INDEX IF NOT EXISTS idx_traces_parent_id ON traces(parent_trace_id);
CREATE INDEX IF NOT EXISTS idx_traces_sequence ON traces(run_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_traces_agent_name ON traces(agent_name);
CREATE INDEX IF NOT EXISTS idx_traces_tool_name ON traces(tool_name);
CREATE INDEX IF NOT EXISTS idx_traces_status ON traces(status);
CREATE INDEX IF NOT EXISTS idx_traces_created_at ON traces(created_at);

-- Insert default sources
INSERT OR IGNORE INTO sources (name, kind, description) VALUES 
    ('Google', 'search', 'Google Search API / Dorking'),
    ('DuckDuckGo', 'search', 'DuckDuckGo Search'),
    ('Recon-ng', 'cli', 'Recon-ng OSINT Framework'),
    ('SpiderFoot', 'cli', 'SpiderFoot OSINT Automation'),
    ('osint-tool', 'cli', 'Generic OSINT Tool CLI'),
    ('WebScraping', 'web', 'Direct web scraping'),
    ('RSS', 'rss', 'RSS/Atom feeds'),
    ('Manual', 'other', 'Manually added items');
"""


class Database:
    """SQLite database manager for OSINT data."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database with given path or default from config."""
        self.db_path = db_path or config.DATABASE_PATH
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Ensure the database directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory configured."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise
        finally:
            conn.close()
    
    def init_schema(self):
        """Initialize the database schema."""
        logger.info(f"Initializing database schema at {self.db_path}")
        with self.transaction() as conn:
            conn.executescript(SCHEMA_SQL)
        logger.info("Database schema initialized successfully")
    
    def execute(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Execute a query and return results."""
        with self.transaction() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
    
    def execute_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute a query and return single result."""
        results = self.execute(query, params)
        return results[0] if results else None
    
    def insert(self, query: str, params: tuple = ()) -> int:
        """Execute an insert and return the last row id."""
        with self.transaction() as conn:
            cursor = conn.execute(query, params)
            return cursor.lastrowid
    
    def update(self, query: str, params: tuple = ()) -> int:
        """Execute an update and return rows affected."""
        with self.transaction() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount


# Singleton database instance
db = Database()


def init_db():
    """Initialize the database (call at app startup)."""
    db.init_schema()


def get_db() -> Database:
    """Get the database instance."""
    return db
