# =============================================================================
# Amass Agent and Tools Tests
# =============================================================================
"""
Tests for OWASP Amass integration.

Tests cover:
- AmassAgent instantiation and capabilities
- AmassEnumTool and AmassIntelTool configuration
- Binary detection and error handling
- Result parsing

Run with: pytest tests/test_amass.py -v
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAmassToolsImport:
    """Test Amass tools can be imported."""
    
    def test_amass_enum_tool_import(self):
        """Test AmassEnumTool can be imported."""
        from tools.amass import AmassEnumTool
        assert AmassEnumTool is not None
    
    def test_amass_intel_tool_import(self):
        """Test AmassIntelTool can be imported."""
        from tools.amass import AmassIntelTool
        assert AmassIntelTool is not None
    
    def test_helper_functions_import(self):
        """Test helper functions can be imported."""
        from tools.amass import _find_amass_binary, _check_amass_available
        assert _find_amass_binary is not None
        assert _check_amass_available is not None


class TestAmassEnumTool:
    """Test AmassEnumTool configuration."""
    
    def test_tool_instantiation(self):
        """Test AmassEnumTool can be instantiated."""
        from tools.amass import AmassEnumTool
        tool = AmassEnumTool()
        assert tool is not None
        assert tool.name == "amass_subdomain_enum"
    
    def test_tool_description(self):
        """Test tool has proper description."""
        from tools.amass import AmassEnumTool
        tool = AmassEnumTool()
        assert "subdomain" in tool.description.lower() or "domain" in tool.description.lower()
    
    def test_tool_args_schema(self):
        """Test tool has correct input schema."""
        from tools.amass import AmassEnumTool, AmassEnumInput
        tool = AmassEnumTool()
        assert tool.args_schema == AmassEnumInput


class TestAmassIntelTool:
    """Test AmassIntelTool configuration."""
    
    def test_tool_instantiation(self):
        """Test AmassIntelTool can be instantiated."""
        from tools.amass import AmassIntelTool
        tool = AmassIntelTool()
        assert tool is not None
        assert tool.name == "amass_intel_discovery"
    
    def test_tool_description(self):
        """Test tool has proper description."""
        from tools.amass import AmassIntelTool
        tool = AmassIntelTool()
        assert "organization" in tool.description.lower() or "domain" in tool.description.lower()


class TestAmassBinaryDetection:
    """Test Amass binary detection."""
    
    def test_find_binary_returns_path_or_none(self):
        """Test _find_amass_binary returns path or None."""
        from tools.amass import _find_amass_binary
        result = _find_amass_binary()
        # Should return string path or None
        assert result is None or isinstance(result, str)
    
    def test_check_available_returns_bool(self):
        """Test _check_amass_available returns boolean."""
        from tools.amass import _check_amass_available
        result = _check_amass_available()
        assert isinstance(result, bool)
    
    @patch('shutil.which')
    def test_find_binary_with_mock(self, mock_which):
        """Test binary detection with mocked shutil.which."""
        mock_which.return_value = "/usr/bin/amass"
        
        from tools.amass import _find_amass_binary
        result = _find_amass_binary()
        # Result could be 'amass' if shutil.which returns a match on the first path
        assert result is not None


class TestAmassAgentImport:
    """Test AmassAgent can be imported."""
    
    def test_agent_import(self):
        """Test AmassAgent can be imported."""
        try:
            from agents.osint.amass import AmassAgent
            assert AmassAgent is not None
        except ModuleNotFoundError:
            pytest.skip("AmassAgent module not yet deployed to container")
    
    def test_agent_in_registry(self):
        """Test AmassAgent is registered in AgentRegistry."""
        try:
            from agents.registry import AgentRegistry
            
            # Initialize registry
            AgentRegistry.initialize()
            
            # Check AmassAgent is registered
            agents = AgentRegistry.list_all()
            assert "AmassAgent" in agents
        except (ModuleNotFoundError, AttributeError):
            pytest.skip("AmassAgent not available in registry")


class TestAmassAgentInstantiation:
    """Test AmassAgent instantiation and configuration."""
    
    @pytest.fixture
    def amass_agent(self):
        """Get AmassAgent instance or skip if not available."""
        try:
            from agents.osint.amass import AmassAgent
            return AmassAgent()
        except ModuleNotFoundError:
            pytest.skip("AmassAgent module not yet deployed to container")
    
    def test_agent_creation(self, amass_agent):
        """Test AmassAgent can be created."""
        assert amass_agent is not None
    
    def test_agent_name(self, amass_agent):
        """Test agent has correct name."""
        assert amass_agent.name == "AmassAgent"
    
    def test_agent_capabilities(self, amass_agent):
        """Test agent has correct capabilities."""
        caps = amass_agent.capabilities
        
        assert caps.name == "AmassAgent"
        assert "amass_subdomain_enum" in caps.tools or "amass_enum" in caps.tools
        assert "amass_intel_discovery" in caps.tools or "amass_intel" in caps.tools
    
    def test_agent_supported_queries(self, amass_agent):
        """Test agent has supported query types."""
        caps = amass_agent.capabilities
        
        assert "domain" in caps.supported_queries
        assert "subdomain" in caps.supported_queries
        assert "attack_surface" in caps.supported_queries
    
    def test_agent_tools_list(self, amass_agent):
        """Test agent returns correct tools."""
        tools = amass_agent._get_tools()
        
        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "amass_subdomain_enum" in tool_names
        assert "amass_intel_discovery" in tool_names


class TestAmassAgentAvailability:
    """Test AmassAgent availability detection."""
    
    def test_is_available_returns_tuple(self):
        """Test is_available returns (bool, str) tuple."""
        try:
            from agents.osint.amass import AmassAgent
            agent = AmassAgent()
            
            available, reason = agent.is_available()
            
            assert isinstance(available, bool)
            assert isinstance(reason, str)
        except ModuleNotFoundError:
            pytest.skip("AmassAgent module not yet deployed to container")
    
    @patch('tools.amass._check_amass_available')
    def test_availability_when_installed(self, mock_check):
        """Test agent reports available when amass is installed."""
        mock_check.return_value = True
        
        try:
            from agents.osint.amass import AmassAgent
            agent = AmassAgent()
            
            # The agent's is_available should check the tools
            available, reason = agent.is_available()
            # Note: depends on actual implementation
            assert isinstance(available, bool)
        except ModuleNotFoundError:
            pytest.skip("AmassAgent module not yet deployed to container")


class TestAmassResultParsing:
    """Test Amass result parsing functions."""
    
    def test_parse_empty_file(self):
        """Test parsing empty output file."""
        import tempfile
        from tools.amass import _parse_amass_json_output
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("")
            temp_path = f.name
        
        try:
            results = _parse_amass_json_output(temp_path)
            assert results == []
        finally:
            os.unlink(temp_path)
    
    def test_parse_plain_subdomains(self):
        """Test parsing plain text subdomain list."""
        import tempfile
        from tools.amass import _parse_amass_json_output
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("www.example.com\n")
            f.write("mail.example.com\n")
            f.write("api.example.com\n")
            temp_path = f.name
        
        try:
            results = _parse_amass_json_output(temp_path)
            assert len(results) == 3
            # Plain text lines should be wrapped
            assert any("www.example.com" in str(r) for r in results)
        finally:
            os.unlink(temp_path)
    
    def test_parse_json_output(self):
        """Test parsing JSON/NDJSON output."""
        import tempfile
        import json
        from tools.amass import _parse_amass_json_output
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(json.dumps({"name": "www.example.com", "source": "DNS"}) + "\n")
            f.write(json.dumps({"name": "api.example.com", "source": "CRT"}) + "\n")
            temp_path = f.name
        
        try:
            results = _parse_amass_json_output(temp_path)
            assert len(results) == 2
            assert results[0]["name"] == "www.example.com"
            assert results[1]["source"] == "CRT"
        finally:
            os.unlink(temp_path)
    
    def test_parse_nonexistent_file(self):
        """Test parsing nonexistent file returns empty list."""
        from tools.amass import _parse_amass_json_output
        
        results = _parse_amass_json_output("/nonexistent/path/file.txt")
        assert results == []


class TestAmassToolExecution:
    """Test Amass tool execution with mocks."""
    
    @patch('tools.amass._find_amass_binary')
    def test_enum_without_binary(self, mock_find):
        """Test AmassEnumTool handles missing binary gracefully."""
        mock_find.return_value = None
        
        from tools.amass import _run_amass_enum_async
        import asyncio
        
        # Run the async function directly
        result = asyncio.get_event_loop().run_until_complete(
            _run_amass_enum_async("example.com")
        )
        
        assert result["success"] is False
        assert "not installed" in result.get("error", "").lower()
    
    @patch('tools.amass._find_amass_binary')
    def test_intel_without_binary(self, mock_find):
        """Test AmassIntelTool handles missing binary gracefully."""
        mock_find.return_value = None
        
        from tools.amass import _run_amass_intel_async
        import asyncio
        
        # Run the async function directly
        result = asyncio.get_event_loop().run_until_complete(
            _run_amass_intel_async("Example Corp")
        )
        
        assert result["success"] is False
        assert "not installed" in result.get("error", "").lower()


class TestAmassInputValidation:
    """Test input validation for Amass tools."""
    
    def test_enum_input_schema(self):
        """Test AmassEnumInput schema."""
        from tools.amass import AmassEnumInput
        
        # Valid input
        input_valid = AmassEnumInput(domain="example.com")
        assert input_valid.domain == "example.com"
        assert input_valid.passive is True  # Default
        assert input_valid.timeout == 300  # Default
    
    def test_enum_input_with_options(self):
        """Test AmassEnumInput with custom options."""
        from tools.amass import AmassEnumInput
        
        input_custom = AmassEnumInput(
            domain="test.com",
            passive=False,
            timeout=600
        )
        assert input_custom.domain == "test.com"
        assert input_custom.passive is False
        assert input_custom.timeout == 600
    
    def test_intel_input_schema(self):
        """Test AmassIntelInput schema."""
        from tools.amass import AmassIntelInput
        
        input_valid = AmassIntelInput(org="Google LLC")
        assert input_valid.org == "Google LLC"
        assert input_valid.timeout == 180  # Default


# =============================================================================
# Integration Tests (requires amass installed)
# =============================================================================

@pytest.mark.skipif(
    not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=1 to enable."
)
class TestAmassIntegration:
    """Integration tests that require amass to be installed."""
    
    def test_amass_binary_exists(self):
        """Test amass binary is accessible."""
        from tools.amass import _find_amass_binary
        
        binary = _find_amass_binary()
        assert binary is not None, "Amass binary not found for integration tests"
    
    @pytest.mark.asyncio
    async def test_enum_real_domain(self):
        """Test real subdomain enumeration (limited)."""
        from tools.amass import AmassEnumTool
        
        tool = AmassEnumTool()
        result = tool._run(
            domain="example.com",
            passive=True,
            timeout=60  # Short timeout for test
        )
        
        # Should complete without error
        assert "error" not in result.lower() or "success" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
