# =============================================================================
# Smoke Tests - Module Loading and Imports
# =============================================================================
"""
Smoke tests for verifying that all modules load correctly.

These tests are designed for CI/CD pipelines to catch import errors,
missing dependencies, and configuration issues early.

Run with: pytest tests/test_smoke.py -v
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfigLoading:
    """Test configuration module loading."""
    
    def test_settings_import(self):
        """Test that settings module can be imported."""
        from config import settings
        assert settings is not None
    
    def test_settings_backward_compat(self):
        """Test backward compatibility with 'config' alias."""
        from config import config
        assert config is not None
    
    def test_settings_properties(self):
        """Test that essential settings properties exist."""
        from config import settings
        
        # Flask settings
        assert hasattr(settings, 'FLASK_DEBUG')
        
        # Database settings
        assert hasattr(settings, 'DATABASE_PATH')
        
        # API Keys (may be None but should exist)
        assert hasattr(settings, 'OPENAI_API_KEY')
        assert hasattr(settings, 'TAVILY_API_KEY')


class TestDatabaseLoading:
    """Test database module loading."""
    
    def test_db_module_import(self):
        """Test database module import."""
        from db import sqlite
        assert sqlite is not None
    
    def test_db_models_import(self):
        """Test database models import."""
        from db.models import OsintResult, ItemType
        assert OsintResult is not None
        assert ItemType is not None
    
    def test_db_repository_import(self):
        """Test repository import."""
        from db.repository import ItemRepository, RunRepository
        assert ItemRepository is not None
        assert RunRepository is not None


class TestToolsLoading:
    """Test tools module loading."""
    
    def test_tools_module_import(self):
        """Test tools package import."""
        import tools
        assert tools is not None
    
    def test_search_tools_import(self):
        """Test search tools import."""
        from tools.search import TavilySearchTool, DuckDuckGoSearchTool
        assert TavilySearchTool is not None
        assert DuckDuckGoSearchTool is not None
    
    def test_scraping_tools_import(self):
        """Test scraping tools import."""
        from tools.scraping import WebScraperTool, GoogleDorkBuilderTool
        assert WebScraperTool is not None
        assert GoogleDorkBuilderTool is not None
    
    def test_analysis_tools_import(self):
        """Test analysis tools import."""
        from tools.analysis import IOCExtractorTool, TagExtractorTool
        assert IOCExtractorTool is not None
        assert TagExtractorTool is not None
    
    def test_maigret_tools_import(self):
        """Test Maigret tools import."""
        from tools.maigret import (
            MaigretUsernameTool,
            MaigretReportTool,
        )
        assert MaigretUsernameTool is not None
        assert MaigretReportTool is not None
    
    def test_bbot_tools_import(self):
        """Test bbot tools import."""
        from tools.bbot import (
            BbotSubdomainTool,
            BbotWebScanTool,
            BbotEmailTool,
        )
        assert BbotSubdomainTool is not None
        assert BbotWebScanTool is not None
        assert BbotEmailTool is not None
    
    def test_telegram_tools_import(self):
        """Test Telegram tools import."""
        from tools.telegram import (
            TelegramMCPSendTool,
            TelegramMCPPublishReportTool,
            TelegramMCPListDialogsTool,
        )
        assert TelegramMCPSendTool is not None
        assert TelegramMCPPublishReportTool is not None
        assert TelegramMCPListDialogsTool is not None


class TestAgentsLoading:
    """Test agents module loading."""
    
    def test_agents_base_import(self):
        """Test base agent classes import."""
        from agents.base import LangChainAgent, AgentCapabilities
        assert LangChainAgent is not None
        assert AgentCapabilities is not None
    
    def test_agents_registry_import(self):
        """Test agent registry import."""
        from agents.registry import AgentRegistry, get_agent, list_agents
        assert AgentRegistry is not None
        assert get_agent is not None
        assert list_agents is not None
    
    def test_osint_agents_import(self):
        """Test OSINT agents import."""
        from agents.osint import (
            TavilySearchAgent,
            DuckDuckGoSearchAgent,
            GoogleDorkingAgent,
            WebScraperAgent,
            ThreatIntelAgent,
            IOCAnalysisAgent,
            HybridOsintAgent,
            ReportGeneratorAgent,
            MaigretAgent,
            BbotAgent,
        )
        assert TavilySearchAgent is not None
        assert DuckDuckGoSearchAgent is not None
        assert GoogleDorkingAgent is not None
        assert WebScraperAgent is not None
        assert ThreatIntelAgent is not None
        assert IOCAnalysisAgent is not None
        assert HybridOsintAgent is not None
        assert ReportGeneratorAgent is not None
        assert MaigretAgent is not None
        assert BbotAgent is not None
    
    def test_control_agent_import(self):
        """Test control agent import."""
        from agents.control import ControlAgent
        assert ControlAgent is not None
    
    def test_consolidator_agent_import(self):
        """Test consolidator agent import."""
        from agents.consolidator import ConsolidatorAgent
        assert ConsolidatorAgent is not None


class TestIntegrationsLoading:
    """Test integrations module loading."""
    
    def test_telegram_integration_import(self):
        """Test Telegram integration import."""
        from integrations.telegram import TelethonClient, TelegramListener
        assert TelethonClient is not None
        assert TelegramListener is not None


class TestFlaskAppLoading:
    """Test Flask app loading."""
    
    def test_flask_app_import(self):
        """Test Flask app import."""
        from app import app
        assert app is not None
        assert app.name == 'app'
    
    def test_api_routes_import(self):
        """Test API routes import."""
        from api import routes
        assert routes is not None


class TestDependencies:
    """Test that required dependencies are available."""
    
    def test_langchain_available(self):
        """Test LangChain is available."""
        import langchain
        assert langchain is not None
    
    def test_langchain_openai_available(self):
        """Test LangChain OpenAI is available."""
        import langchain_openai
        assert langchain_openai is not None
    
    def test_langgraph_available(self):
        """Test LangGraph is available."""
        import langgraph
        assert langgraph is not None
    
    def test_flask_available(self):
        """Test Flask is available."""
        import flask
        assert flask is not None
    
    def test_requests_available(self):
        """Test requests is available."""
        import requests
        assert requests is not None
    
    def test_beautifulsoup_available(self):
        """Test BeautifulSoup is available."""
        from bs4 import BeautifulSoup
        assert BeautifulSoup is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
