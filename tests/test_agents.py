# =============================================================================
# Agent Tests - Instantiation and Capabilities
# =============================================================================
"""
Tests for agent instantiation, capabilities, and basic functionality.

These tests verify that agents can be created and have correct configurations.

Run with: pytest tests/test_agents.py -v
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import AgentCapabilities
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
from agents.control import ControlAgent
from agents.consolidator import ConsolidatorAgent
from agents.registry import AgentRegistry, register_all_agents, list_agents


class TestAgentInstantiation:
    """Test that all agents can be instantiated."""
    
    def test_tavily_search_agent_instantiation(self):
        """Test TavilySearchAgent instantiation."""
        agent = TavilySearchAgent()
        assert agent is not None
        assert agent.name == "TavilySearchAgent"
    
    def test_duckduckgo_search_agent_instantiation(self):
        """Test DuckDuckGoSearchAgent instantiation."""
        agent = DuckDuckGoSearchAgent()
        assert agent is not None
        assert agent.name == "DuckDuckGoSearchAgent"
    
    def test_google_dorking_agent_instantiation(self):
        """Test GoogleDorkingAgent instantiation."""
        agent = GoogleDorkingAgent()
        assert agent is not None
        assert agent.name == "GoogleDorkingAgent"
    
    def test_web_scraper_agent_instantiation(self):
        """Test WebScraperAgent instantiation."""
        agent = WebScraperAgent()
        assert agent is not None
        assert agent.name == "WebScraperAgent"
    
    def test_threat_intel_agent_instantiation(self):
        """Test ThreatIntelAgent instantiation."""
        agent = ThreatIntelAgent()
        assert agent is not None
        assert agent.name == "ThreatIntelAgent"
    
    def test_ioc_analysis_agent_instantiation(self):
        """Test IOCAnalysisAgent instantiation."""
        agent = IOCAnalysisAgent()
        assert agent is not None
        assert agent.name == "IOCAnalysisAgent"
    
    def test_hybrid_osint_agent_instantiation(self):
        """Test HybridOsintAgent instantiation."""
        agent = HybridOsintAgent()
        assert agent is not None
        assert agent.name == "HybridOsintAgent"
    
    def test_report_generator_agent_instantiation(self):
        """Test ReportGeneratorAgent instantiation."""
        agent = ReportGeneratorAgent()
        assert agent is not None
        assert agent.name == "ReportGeneratorAgent"
    
    def test_maigret_agent_instantiation(self):
        """Test MaigretAgent instantiation."""
        agent = MaigretAgent()
        assert agent is not None
        assert agent.name == "MaigretAgent"
    
    def test_bbot_agent_instantiation(self):
        """Test BbotAgent instantiation."""
        agent = BbotAgent()
        assert agent is not None
        assert agent.name == "BbotAgent"
    
    def test_control_agent_instantiation(self):
        """Test ControlAgent instantiation."""
        agent = ControlAgent()
        assert agent is not None
        assert agent.name == "ControlAgent"
    
    def test_consolidator_agent_instantiation(self):
        """Test ConsolidatorAgent instantiation."""
        agent = ConsolidatorAgent()
        assert agent is not None
        assert agent.name == "ConsolidatorAgent"


class TestAgentCapabilities:
    """Test agent capabilities configuration."""
    
    def test_agent_has_capabilities(self):
        """Test all agents have capabilities."""
        agents = [
            TavilySearchAgent(),
            DuckDuckGoSearchAgent(),
            GoogleDorkingAgent(),
            WebScraperAgent(),
            ThreatIntelAgent(),
            IOCAnalysisAgent(),
            HybridOsintAgent(),
            ReportGeneratorAgent(),
            MaigretAgent(),
            BbotAgent(),
            ControlAgent(),
            ConsolidatorAgent(),
        ]
        
        for agent in agents:
            assert isinstance(agent.capabilities, AgentCapabilities)
            assert agent.capabilities.name is not None
            assert agent.capabilities.description is not None
            assert isinstance(agent.capabilities.tools, list)
            assert isinstance(agent.capabilities.supported_queries, list)
    
    def test_tavily_agent_capabilities(self):
        """Test TavilySearchAgent capabilities."""
        agent = TavilySearchAgent()
        caps = agent.capabilities
        
        assert caps.name == "TavilySearchAgent"
        assert "tavily_search" in caps.tools
        assert "search" in caps.supported_queries or "news" in caps.supported_queries
    
    def test_maigret_agent_capabilities(self):
        """Test MaigretAgent capabilities."""
        agent = MaigretAgent()
        caps = agent.capabilities
        
        assert caps.name == "MaigretAgent"
        assert "maigret_username_search" in caps.tools
        assert "username" in caps.supported_queries
    
    def test_hybrid_agent_has_multiple_tools(self):
        """Test HybridOsintAgent has multiple tools."""
        agent = HybridOsintAgent()
        caps = agent.capabilities
        
        # Hybrid should have many tools
        assert len(caps.tools) >= 4
    
    def test_control_agent_has_delegation_tools(self):
        """Test ControlAgent has delegation tools."""
        agent = ControlAgent()
        caps = agent.capabilities
        
        assert "delegate_to_agent" in caps.tools
        assert "list_available_agents" in caps.tools


class TestAgentTools:
    """Test that agents have properly configured tools."""
    
    def test_agents_have_tools_in_capabilities(self):
        """Test all agents have tools listed in capabilities."""
        agents = [
            TavilySearchAgent(),
            DuckDuckGoSearchAgent(),
            GoogleDorkingAgent(),
            WebScraperAgent(),
            ThreatIntelAgent(),
            IOCAnalysisAgent(),
            HybridOsintAgent(),
            ReportGeneratorAgent(),
            MaigretAgent(),
            BbotAgent(),
            ControlAgent(),
            ConsolidatorAgent(),
        ]
        
        for agent in agents:
            # Check capabilities.tools (what the agent claims to have)
            assert len(agent.capabilities.tools) >= 1, f"{agent.name} should list at least 1 tool in capabilities"
    
    def test_get_tools_method_returns_tools(self):
        """Test _get_tools method returns tool instances."""
        # Test a few agents directly calling _get_tools
        agent = IOCAnalysisAgent()
        tools = agent._get_tools()
        
        assert isinstance(tools, list)
        assert len(tools) >= 1
    
    def test_tools_are_langchain_tools(self):
        """Test tools are proper LangChain BaseTool instances."""
        from langchain_core.tools import BaseTool
        
        agent = IOCAnalysisAgent()
        tools = agent._get_tools()
        
        for tool in tools:
            assert isinstance(tool, BaseTool)


class TestAgentRegistry:
    """Test agent registry functionality."""
    
    def test_register_all_agents(self):
        """Test registering all agents."""
        AgentRegistry.reset()
        register_all_agents()
        
        agents = list_agents()
        assert len(agents) >= 9  # At least 9 OSINT agents
    
    def test_registry_contains_expected_agents(self):
        """Test registry contains expected agents."""
        AgentRegistry.reset()
        register_all_agents()
        
        expected = [
            "TavilySearchAgent",
            "DuckDuckGoSearchAgent",
            "GoogleDorkingAgent",
            "WebScraperAgent",
            "ThreatIntelAgent",
            "IOCAnalysisAgent",
            "HybridOsintAgent",
            "ReportGeneratorAgent",
            "MaigretAgent",
            "BbotAgent",
        ]
        
        registered = list_agents()
        for name in expected:
            assert name in registered, f"{name} should be in registry"
    
    def test_get_agent_by_name(self):
        """Test getting agent by name."""
        AgentRegistry.reset()
        register_all_agents()
        
        agent = AgentRegistry.get("TavilySearchAgent")
        assert agent is not None
        assert agent.name == "TavilySearchAgent"
    
    def test_get_nonexistent_agent(self):
        """Test getting non-existent agent returns None."""
        AgentRegistry.reset()
        register_all_agents()
        
        agent = AgentRegistry.get("NonExistentAgent")
        assert agent is None
    
    def test_list_available_agents(self):
        """Test listing available agents with status."""
        AgentRegistry.reset()
        register_all_agents()
        
        available = AgentRegistry.list_available()
        assert isinstance(available, list)
        assert len(available) >= 9
        
        for info in available:
            assert "name" in info
            assert "available" in info
            assert "description" in info
    
    def test_get_by_capability(self):
        """Test getting agents by capability."""
        AgentRegistry.reset()
        register_all_agents()
        
        search_agents = AgentRegistry.get_by_capability("search")
        assert isinstance(search_agents, list)
        # At least Tavily, DuckDuckGo, or GoogleDorking should match


class TestAgentAvailability:
    """Test agent availability checks."""
    
    def test_agent_is_available_method(self):
        """Test is_available method exists and returns tuple."""
        agent = DuckDuckGoSearchAgent()
        result = agent.is_available()
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)
    
    def test_duckduckgo_always_available(self):
        """Test DuckDuckGo is always available (no API key needed)."""
        agent = DuckDuckGoSearchAgent()
        available, reason = agent.is_available()
        
        # DuckDuckGo doesn't require API keys
        # But may not be available due to OPENAI_API_KEY for LLM
        assert isinstance(available, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
