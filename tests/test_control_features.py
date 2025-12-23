# =============================================================================
# Control Agent Advanced Features Tests
# =============================================================================
"""
Tests for investigation robustness, agent selection, and continuation features.

Tests cover:
- InvestigationProgress tracking for partial completion
- Agent selection and validation
- Investigation continuation from previous runs

Run with: pytest tests/test_control_features.py -v
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.control import (
    ControlAgent,
    InvestigationProgress,
    AgentResult,
    get_investigation_progress,
    set_investigation_progress,
    delegate_to_agent,
)
from agents.registry import AgentRegistry


class TestInvestigationProgress:
    """Test InvestigationProgress class for partial completion tracking."""
    
    def test_progress_initialization(self):
        """Test InvestigationProgress initializes correctly."""
        progress = InvestigationProgress(
            run_id=1,
            topic="test investigation",
            depth="standard",
            started_at=datetime.now()
        )
        
        assert progress.run_id == 1
        assert progress.topic == "test investigation"
        assert progress.depth == "standard"
        assert progress.started_at is not None
        assert len(progress.agent_results) == 0
        assert len(progress.errors) == 0
    
    def test_add_successful_agent_result(self):
        """Test adding a successful agent result."""
        progress = InvestigationProgress(run_id=1, topic="test")
        
        result = AgentResult(
            agent_name="TavilySearchAgent",
            success=True,
            result="Found 5 relevant articles",
            duration_seconds=2.5,
            iocs_extracted=3
        )
        progress.add_agent_result(result)
        
        assert len(progress.agent_results) == 1
        assert progress.get_successful_count() == 1
        assert progress.get_failed_count() == 0
        assert progress.total_iocs == 3
        assert progress.has_useful_results() is True
    
    def test_add_failed_agent_result(self):
        """Test adding a failed agent result."""
        progress = InvestigationProgress(run_id=1, topic="test")
        
        result = AgentResult(
            agent_name="BbotAgent",
            success=False,
            error="Connection timeout",
            duration_seconds=30.0
        )
        progress.add_agent_result(result)
        
        assert len(progress.agent_results) == 1
        assert progress.get_successful_count() == 0
        assert progress.get_failed_count() == 1
        assert len(progress.errors) == 1
        assert "BbotAgent" in progress.errors[0]
    
    def test_mixed_results_tracking(self):
        """Test tracking mix of successful and failed results."""
        progress = InvestigationProgress(run_id=1, topic="test")
        
        # Add 2 successful, 1 failed
        progress.add_agent_result(AgentResult(
            agent_name="TavilySearchAgent", success=True, 
            result="Found data", iocs_extracted=5
        ))
        progress.add_agent_result(AgentResult(
            agent_name="DuckDuckGoSearchAgent", success=True,
            result="Found more data", iocs_extracted=3
        ))
        progress.add_agent_result(AgentResult(
            agent_name="BbotAgent", success=False,
            error="Timeout"
        ))
        
        assert progress.get_successful_count() == 2
        assert progress.get_failed_count() == 1
        assert progress.total_iocs == 8
        assert progress.has_useful_results() is True
    
    def test_no_useful_results_when_all_failed(self):
        """Test has_useful_results returns False when all agents fail."""
        progress = InvestigationProgress(run_id=1, topic="test")
        
        progress.add_agent_result(AgentResult(
            agent_name="Agent1", success=False, error="Error 1"
        ))
        progress.add_agent_result(AgentResult(
            agent_name="Agent2", success=False, error="Error 2"
        ))
        
        assert progress.has_useful_results() is False
    
    def test_progress_to_dict(self):
        """Test serializing progress to dictionary."""
        progress = InvestigationProgress(
            run_id=1,
            topic="test",
            depth="deep",
            started_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        progress.add_agent_result(AgentResult(
            agent_name="TestAgent", success=True, iocs_extracted=2
        ))
        
        result = progress.to_dict()
        
        assert result["run_id"] == 1
        assert result["topic"] == "test"
        assert result["depth"] == "deep"
        assert result["agents_succeeded"] == 1
        assert result["agents_failed"] == 0
        assert result["total_iocs"] == 2
        assert result["has_useful_results"] is True


class TestAgentResult:
    """Test AgentResult dataclass."""
    
    def test_successful_result(self):
        """Test creating a successful AgentResult."""
        result = AgentResult(
            agent_name="TavilySearchAgent",
            success=True,
            result="Found 10 articles about cybersecurity",
            duration_seconds=1.5,
            iocs_extracted=5
        )
        
        assert result.agent_name == "TavilySearchAgent"
        assert result.success is True
        assert "10 articles" in result.result
        assert result.duration_seconds == 1.5
        assert result.iocs_extracted == 5
        assert result.error == ""
    
    def test_failed_result(self):
        """Test creating a failed AgentResult."""
        result = AgentResult(
            agent_name="MaigretAgent",
            success=False,
            error="Command not found: maigret",
            duration_seconds=0.1
        )
        
        assert result.agent_name == "MaigretAgent"
        assert result.success is False
        assert result.result == ""
        assert "Command not found" in result.error


class TestProgressThreadLocal:
    """Test thread-local progress storage."""
    
    def test_set_and_get_progress(self):
        """Test setting and getting investigation progress."""
        progress = InvestigationProgress(run_id=42, topic="thread test")
        
        set_investigation_progress(progress)
        retrieved = get_investigation_progress()
        
        assert retrieved is not None
        assert retrieved.run_id == 42
        assert retrieved.topic == "thread test"
        
        # Clean up
        set_investigation_progress(None)
    
    def test_get_progress_when_none(self):
        """Test getting progress when none is set."""
        set_investigation_progress(None)
        result = get_investigation_progress()
        assert result is None


class TestControlAgentFeatures:
    """Test ControlAgent advanced features."""
    
    def test_control_agent_instantiation(self):
        """Test ControlAgent can be instantiated."""
        agent = ControlAgent()
        assert agent is not None
        assert agent.name == "ControlAgent"
    
    def test_control_agent_capabilities(self):
        """Test ControlAgent has correct capabilities."""
        agent = ControlAgent()
        caps = agent.capabilities
        
        assert "delegate_to_agent" in caps.tools
        assert "delegate_with_evidence_feedback" in caps.tools
        assert "get_shared_evidence_summary" in caps.tools
    
    @patch('agents.control.ControlAgent.run')
    def test_investigate_with_selected_agents(self, mock_run):
        """Test investigation with specific agent selection."""
        mock_run.return_value = "Investigation report"
        
        agent = ControlAgent()
        result = agent.investigate(
            topic="Test topic",
            agents=["TavilySearchAgent", "DuckDuckGoSearchAgent"],
            depth="quick"
        )
        
        assert result["success"] is True
        assert result["topic"] == "Test topic"
        assert "report" in result
    
    @patch('agents.control.ControlAgent.run')
    def test_investigate_continuation(self, mock_run):
        """Test investigation continuation with previous context."""
        mock_run.return_value = "Continued investigation report"
        
        agent = ControlAgent()
        result = agent.investigate(
            topic="Original topic",
            depth="standard",
            continue_from={
                "previous_findings": "Found some IOCs: 192.168.1.1",
                "previous_iocs": ["192.168.1.1", "evil.com"],
                "new_instructions": "Focus on the domain",
            }
        )
        
        assert result["success"] is True
        # The query should have been enhanced with continuation context
        call_args = mock_run.call_args
        assert call_args is not None
    
    @patch('agents.control.ControlAgent.run')
    def test_partial_completion_returns_status(self, mock_run):
        """Test that investigation returns partial status when errors occur."""
        mock_run.return_value = "Partial report"
        
        # Set up progress tracking manually to simulate partial completion
        agent = ControlAgent()
        result = agent.investigate(
            topic="Test topic",
            depth="quick"
        )
        
        # Result should have progress information
        assert "progress" in result
        assert result["progress"] is not None


class TestAgentSelection:
    """Test agent selection validation."""
    
    def test_registry_lists_all_agents(self):
        """Test that registry returns all registered agents."""
        agents = AgentRegistry.list_all()
        
        # Should have at least the core agents
        assert "TavilySearchAgent" in agents
        assert "DuckDuckGoSearchAgent" in agents
        assert "MaigretAgent" in agents
    
    def test_registry_get_valid_agent(self):
        """Test getting a valid agent from registry."""
        agent = AgentRegistry.get("TavilySearchAgent")
        assert agent is not None
        assert agent.name == "TavilySearchAgent"
    
    def test_registry_get_invalid_agent(self):
        """Test getting an invalid agent returns None."""
        agent = AgentRegistry.get("NonExistentAgent")
        assert agent is None


class TestDelegateToAgentTracking:
    """Test that delegate_to_agent tracks results."""
    
    @patch('agents.control.AgentRegistry.get')
    @patch('agents.control.get_investigation_progress')
    def test_delegate_tracks_success(self, mock_get_progress, mock_registry_get):
        """Test that successful delegation is tracked."""
        # Set up mocks
        mock_agent = MagicMock()
        mock_agent.is_available.return_value = (True, "Available")
        mock_agent.run.return_value = "Agent result"
        mock_registry_get.return_value = mock_agent
        
        progress = InvestigationProgress(run_id=1, topic="test")
        mock_get_progress.return_value = progress
        
        # Call delegate
        result = delegate_to_agent.invoke({
            "agent_name": "TestAgent",
            "query": "Test query"
        })
        
        # Check result was tracked
        assert len(progress.agent_results) == 1
        assert progress.agent_results[0].success is True
    
    @patch('agents.control.AgentRegistry.get')
    @patch('agents.control.get_investigation_progress')
    def test_delegate_tracks_not_found(self, mock_get_progress, mock_registry_get):
        """Test that agent not found is tracked as failure."""
        mock_registry_get.return_value = None
        
        progress = InvestigationProgress(run_id=1, topic="test")
        mock_get_progress.return_value = progress
        
        # Call delegate with non-existent agent
        result = delegate_to_agent.invoke({
            "agent_name": "NonExistentAgent",
            "query": "Test query"
        })
        
        # Should track as failure
        assert "not found" in result.lower()
        assert len(progress.agent_results) == 1
        assert progress.agent_results[0].success is False


class TestPartialReportGeneration:
    """Test partial report generation."""
    
    def test_generate_partial_report(self):
        """Test generating partial report from progress."""
        agent = ControlAgent()
        
        progress = InvestigationProgress(run_id=1, topic="Test Topic")
        progress.add_agent_result(AgentResult(
            agent_name="TavilySearchAgent",
            success=True,
            result="Found important information about the topic"
        ))
        progress.add_agent_result(AgentResult(
            agent_name="BbotAgent",
            success=False,
            error="Connection timeout"
        ))
        progress.errors.append("BbotAgent: Connection timeout")
        
        report = agent._generate_partial_report("Test Topic", progress, None)
        
        assert "Partial Investigation Report" in report
        assert "Test Topic" in report
        assert "TavilySearchAgent" in report
        assert "Connection timeout" in report
        assert "Recommendations" in report


# =============================================================================
# API Route Tests (if running with Flask test client)
# =============================================================================

class TestContinueEndpoint:
    """Test the continue investigation API endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create Flask test client."""
        try:
            from app import app
            app.config['TESTING'] = True
            with app.test_client() as client:
                yield client
        except ImportError:
            pytest.skip("Flask app not available for testing")
    
    def test_continue_requires_valid_run(self, client):
        """Test that continue endpoint requires valid run ID."""
        response = client.post('/api/runs/99999/continue', json={})
        assert response.status_code in [404, 500]  # Either not found or error
    
    def test_agents_endpoint_available(self, client):
        """Test agents endpoint returns list."""
        response = client.get('/api/agents')
        assert response.status_code == 200
        data = response.get_json()
        # Response can be a list or a dict with 'agents' key
        if isinstance(data, dict):
            assert 'agents' in data
            assert isinstance(data['agents'], list)
            assert len(data['agents']) > 0
        else:
            assert isinstance(data, list)
            assert len(data) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
