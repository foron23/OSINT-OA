# =============================================================================
# OSINT News Aggregator - Base Tool Definitions
# =============================================================================
"""
Base classes and input schemas for LangChain tools.

This module provides:
- Pydantic models for tool inputs
- Base tool utilities
"""

from pydantic import BaseModel, Field
from typing import Optional, List


# =============================================================================
# Input Schemas (Pydantic Models)
# =============================================================================

class ToolInput(BaseModel):
    """Base input for all tools."""
    pass


class WebSearchInput(BaseModel):
    """Input schema for web search tools."""
    query: str = Field(description="The search query")
    max_results: int = Field(default=10, description="Maximum number of results to return")


class UrlInput(BaseModel):
    """Input schema for URL-based tools."""
    url: str = Field(description="The URL to process")


class TextAnalysisInput(BaseModel):
    """Input schema for text analysis tools."""
    text: str = Field(description="The text to analyze")


class TelegramInput(BaseModel):
    """Input schema for Telegram publishing."""
    message: str = Field(description="The message to publish")
    chat_id: Optional[str] = Field(default=None, description="Target chat ID (optional)")


class GoogleDorkInput(BaseModel):
    """Input schema for Google dork builder."""
    base_query: str = Field(description="Base search terms")
    site: Optional[str] = Field(default=None, description="Limit to specific site")
    filetype: Optional[str] = Field(default=None, description="File type filter (e.g., pdf, doc)")
    intitle: Optional[str] = Field(default=None, description="Must appear in page title")
    inurl: Optional[str] = Field(default=None, description="Must appear in URL")


class OSRFInput(BaseModel):
    """Input schema for OSRFramework tools."""
    target: str = Field(description="The target to investigate (username, email, domain, etc.)")
    platforms: Optional[List[str]] = Field(default=None, description="Specific platforms to check")


class MCPToolInput(BaseModel):
    """Input schema for MCP tool calls."""
    tool_name: str = Field(description="Name of the MCP tool to call")
    arguments: dict = Field(default_factory=dict, description="Arguments to pass to the tool")
