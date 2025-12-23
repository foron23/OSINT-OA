# =============================================================================
# OSINT OA - Agent Registry
# =============================================================================
"""
Agent registry for discovering and accessing agents.

Provides:
- AgentRegistry: Central registry of all agents
- get_agent: Get agent by name
- list_agents: List all available agents
"""

import logging
from typing import Dict, List, Optional, Type, Any

from agents.base import LangChainAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for all OSINT agents.
    
    Provides agent discovery, instantiation, and lifecycle management.
    """
    
    _agents: Dict[str, LangChainAgent] = {}
    _agent_classes: Dict[str, Type[LangChainAgent]] = {}
    _initialized: bool = False
    
    @classmethod
    def register(cls, agent_class: Type[LangChainAgent]) -> None:
        """
        Register an agent class.
        
        Args:
            agent_class: The agent class to register
        """
        try:
            # Create instance to get capabilities
            instance = agent_class()
            name = instance.name
            cls._agents[name] = instance
            cls._agent_classes[name] = agent_class
            logger.debug(f"Registered agent: {name}")
        except Exception as e:
            logger.warning(f"Failed to register {agent_class.__name__}: {e}")
    
    @classmethod
    def get(cls, name: str) -> Optional[LangChainAgent]:
        """
        Get an agent by name.
        
        Args:
            name: Agent name
            
        Returns:
            Agent instance or None
        """
        cls._ensure_initialized()
        return cls._agents.get(name)
    
    @classmethod
    def list_all(cls) -> List[str]:
        """
        List all registered agent names.
        
        Returns:
            List of agent names
        """
        cls._ensure_initialized()
        return list(cls._agents.keys())
    
    @classmethod
    def list_available(cls) -> List[Dict[str, Any]]:
        """
        List all available agents with their status.
        
        Returns:
            List of dicts with agent info and availability
        """
        cls._ensure_initialized()
        result = []
        
        for name, agent in cls._agents.items():
            available, reason = agent.is_available()
            result.append({
                "name": name,
                "available": available,
                "reason": reason,
                "description": agent.capabilities.description,
                "tools": agent.capabilities.tools,
            })
        
        return result
    
    @classmethod
    def get_by_capability(cls, query_type: str) -> List[LangChainAgent]:
        """
        Get agents that support a specific query type.
        
        Args:
            query_type: Type of query (e.g., "search", "ioc", "threat")
            
        Returns:
            List of agents supporting the query type
        """
        cls._ensure_initialized()
        matching = []
        
        for agent in cls._agents.values():
            if query_type in agent.capabilities.supported_queries:
                matching.append(agent)
        
        return matching
    
    @classmethod
    def _ensure_initialized(cls) -> None:
        """Ensure agents are registered."""
        if not cls._initialized:
            register_all_agents()
            cls._initialized = True
    
    @classmethod
    def reset(cls) -> None:
        """Reset the registry (for testing)."""
        cls._agents.clear()
        cls._agent_classes.clear()
        cls._initialized = False


def get_agent(name: str) -> Optional[LangChainAgent]:
    """
    Get an agent by name.
    
    Convenience function for AgentRegistry.get().
    
    Args:
        name: Agent name
        
    Returns:
        Agent instance or None
    """
    return AgentRegistry.get(name)


def list_agents() -> List[str]:
    """
    List all registered agent names.
    
    Convenience function for AgentRegistry.list_all().
    """
    return AgentRegistry.list_all()


def register_all_agents() -> None:
    """
    Register all available agent classes.
    
    Called automatically on first registry access.
    """
    if AgentRegistry._initialized:
        return
    
    try:
        # Import and register OSINT agents
        from agents.osint.search import (
            TavilySearchAgent,
            DuckDuckGoSearchAgent,
            GoogleDorkingAgent,
        )
        from agents.osint.analysis import (
            WebScraperAgent,
            ThreatIntelAgent,
            IOCAnalysisAgent,
        )
        from agents.osint.hybrid import HybridOsintAgent
        from agents.osint.report import ReportGeneratorAgent
        
        # Modern OSINT agents (replacing OSRFramework)
        from agents.osint.maigret import MaigretAgent
        from agents.osint.bbot import BbotAgent
        from agents.osint.amass import AmassAgent
        
        # Email and Phone OSINT agents
        from agents.osint.holehe import HoleheAgent
        from agents.osint.phoneinfoga import PhoneInfogaAgent
        
        # Register each agent
        for agent_class in [
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
            AmassAgent,
            HoleheAgent,
            PhoneInfogaAgent,
        ]:
            AgentRegistry.register(agent_class)
        
        AgentRegistry._initialized = True
        logger.info(f"Registered {len(AgentRegistry._agents)} agents")
        
    except Exception as e:
        logger.error(f"Failed to register agents: {e}")


# Backward compatibility alias
LangChainAgentRegistry = AgentRegistry
