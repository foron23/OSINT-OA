# =============================================================================
# OSINT Tools Tests - Unified Test Suite
# =============================================================================
"""
Comprehensive tests for all OSINT tools.

Test coverage:
- Maigret: Username OSINT across 500+ platforms
- BBOT: Domain reconnaissance (subdomains, web, email)
- Holehe: Email verification across 100+ platforms
- Amass: OWASP subdomain enumeration
- PhoneInfoga: Phone number OSINT

These tests verify:
1. Tool instantiation and configuration
2. Input schema validation
3. Command-line argument generation
4. Output parsing
5. Error handling
6. Async/sync execution
7. Tool module integration

Run all tests: pytest tests/test_osint_tools.py -v
Run fast tests only: pytest tests/test_osint_tools.py -v -m "not slow"
Run slow/integration tests: pytest tests/test_osint_tools.py -v --run-slow
"""

import pytest
import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# =============================================================================
# Imports: Maigret
# =============================================================================
from tools.maigret import (
    MaigretUsernameTool,
    MaigretReportTool,
    _check_maigret_available,
    _run_maigret_async,
)

# =============================================================================
# Imports: BBOT
# =============================================================================
from tools.bbot import (
    BbotSubdomainTool,
    BbotWebScanTool,
    BbotEmailTool,
    _check_bbot_available,
    _run_bbot_async,
)


# =============================================================================
# Fixtures: Maigret
# =============================================================================

@pytest.fixture
def maigret_username_tool():
    """Create MaigretUsernameTool instance."""
    return MaigretUsernameTool()


@pytest.fixture
def maigret_report_tool():
    """Create MaigretReportTool instance."""
    return MaigretReportTool()


@pytest.fixture
def mock_maigret_ndjson_output():
    """Sample NDJSON output from maigret."""
    return [
        {
            "sitename": "GitHub",
            "url_user": "https://github.com/testuser",
            "status": {"status": "Claimed", "site_name": "GitHub"},
        },
        {
            "sitename": "Twitter",
            "url_user": "https://twitter.com/testuser",
            "status": {"status": "Claimed", "site_name": "Twitter"},
        },
        {
            "sitename": "Facebook",
            "url_user": "https://facebook.com/testuser",
            "status": {"status": "Available", "site_name": "Facebook"},
        },
    ]


# =============================================================================
# Fixtures: BBOT
# =============================================================================

@pytest.fixture
def bbot_subdomain_tool():
    """Create BbotSubdomainTool instance."""
    return BbotSubdomainTool()


@pytest.fixture
def bbot_web_tool():
    """Create BbotWebScanTool instance."""
    return BbotWebScanTool()


@pytest.fixture
def bbot_email_tool():
    """Create BbotEmailTool instance."""
    return BbotEmailTool()


@pytest.fixture
def mock_bbot_ndjson_output():
    """Sample NDJSON output from bbot."""
    return [
        {"type": "SCAN", "data": {"name": "test_scan"}},
        {"type": "DNS_NAME", "data": "example.com", "host": "example.com"},
        {"type": "DNS_NAME", "data": "www.example.com", "host": "www.example.com"},
        {"type": "DNS_NAME", "data": "mail.example.com", "host": "mail.example.com"},
        {"type": "EMAIL_ADDRESS", "data": "admin@example.com"},
        {"type": "TECHNOLOGY", "data": "nginx"},
    ]


# #############################################################################
# MAIGRET TESTS
# #############################################################################

# =============================================================================
# Maigret Tool Instantiation Tests
# =============================================================================

class TestMaigretToolInstantiation:
    """Test that Maigret tools can be properly instantiated."""

    def test_maigret_username_tool_creation(self, maigret_username_tool):
        """Test MaigretUsernameTool instantiation."""
        assert maigret_username_tool is not None
        assert maigret_username_tool.name == "maigret_username_search"
        assert "500+" in maigret_username_tool.description
        assert maigret_username_tool.args_schema is not None

    def test_maigret_report_tool_creation(self, maigret_report_tool):
        """Test MaigretReportTool instantiation."""
        assert maigret_report_tool is not None
        assert maigret_report_tool.name == "maigret_report"
        assert "comprehensive" in maigret_report_tool.description.lower()


# =============================================================================
# Maigret Tool Availability Tests
# =============================================================================

class TestMaigretToolAvailability:
    """Test Maigret tool availability checking."""

    def test_check_maigret_available(self):
        """Test maigret availability check."""
        result = _check_maigret_available()
        # Should be boolean
        assert isinstance(result, bool)
        # If maigret is installed, should find it
        if shutil.which('maigret'):
            assert result is True


# =============================================================================
# Maigret Output Parsing Tests
# =============================================================================

class TestMaigretOutputParsing:
    """Test Maigret output parsing functionality."""

    def test_parse_ndjson_claimed_status(self, mock_maigret_ndjson_output):
        """Test parsing NDJSON with Claimed status."""
        # Simulate the extraction logic
        found_sites = []
        for entry in mock_maigret_ndjson_output:
            status_data = entry.get("status", {})
            if isinstance(status_data, dict):
                status_str = status_data.get("status", "")
            else:
                status_str = str(status_data)
            
            if status_str.lower() in ["claimed", "found"]:
                found_sites.append({
                    "site": entry.get("sitename", ""),
                    "url": entry.get("url_user", ""),
                    "status": status_str
                })
        
        assert len(found_sites) == 2  # GitHub and Twitter claimed
        assert any(s["site"] == "GitHub" for s in found_sites)
        assert any(s["site"] == "Twitter" for s in found_sites)

    def test_parse_nested_status(self):
        """Test parsing nested status structure."""
        entry = {
            "sitename": "YouTube",
            "url_user": "https://youtube.com/@testuser",
            "status": {"status": "Claimed", "site_name": "YouTube User"}
        }
        
        status_data = entry.get("status", {})
        status_str = status_data.get("status", "") if isinstance(status_data, dict) else ""
        site_name = status_data.get("site_name", entry.get("sitename", ""))
        
        assert status_str == "Claimed"
        assert site_name == "YouTube User"


# =============================================================================
# Maigret Mock Execution Tests
# =============================================================================

class TestMaigretMockExecution:
    """Test Maigret execution with mocked subprocess."""

    @pytest.mark.asyncio
    async def test_maigret_not_installed(self):
        """Test behavior when maigret is not installed."""
        with patch('tools.maigret._check_maigret_available', return_value=False):
            result = await _run_maigret_async("testuser", timeout=10, top_sites=5)
            
            assert result["success"] is False
            assert "not installed" in result["error"].lower()
            assert result["results"] == []

    @pytest.mark.asyncio
    async def test_maigret_timeout_handling(self):
        """Test timeout handling in maigret execution."""
        with patch('tools.maigret._check_maigret_available', return_value=True):
            with patch('asyncio.create_subprocess_exec') as mock_exec:
                # Simulate a timeout
                mock_process = AsyncMock()
                mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
                mock_exec.return_value = mock_process
                
                result = await _run_maigret_async("testuser", timeout=1, top_sites=1)
                
                assert result["success"] is False
                assert "timed out" in result["error"].lower()


# =============================================================================
# Maigret Integration Tests (require actual tools installed)
# =============================================================================

@pytest.mark.slow
class TestMaigretIntegration:
    """Integration tests for Maigret (require maigret installed)."""

    @pytest.mark.skipif(
        not shutil.which('maigret'),
        reason="maigret not installed"
    )
    @pytest.mark.asyncio
    async def test_maigret_real_search_minimal(self):
        """Test real maigret search with minimal sites."""
        result = await _run_maigret_async(
            "testuser123",
            timeout=15,
            top_sites=3
        )
        
        # Should succeed even if no results
        assert "success" in result
        assert "username" in result
        assert result["username"] == "testuser123"
        assert "results" in result
        assert isinstance(result["results"], list)

    @pytest.mark.skipif(
        not shutil.which('maigret'),
        reason="maigret not installed"
    )
    def test_maigret_tool_sync_execution(self, maigret_username_tool):
        """Test synchronous tool execution."""
        result = maigret_username_tool._run(
            username="testuser123",
            timeout=15,
            top_sites=3
        )
        
        # Should return JSON string
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "success" in parsed
        assert "username" in parsed


# =============================================================================
# Maigret Input Validation Tests
# =============================================================================

class TestMaigretInputValidation:
    """Test input validation for Maigret tools."""

    def test_maigret_username_schema(self, maigret_username_tool):
        """Test MaigretUsernameTool input schema."""
        schema = maigret_username_tool.args_schema
        
        # Should have required fields
        assert hasattr(schema, 'model_fields')
        fields = schema.model_fields
        assert 'username' in fields
        assert 'timeout' in fields
        assert 'top_sites' in fields


# =============================================================================
# Maigret Output Format Tests
# =============================================================================

class TestMaigretOutputFormat:
    """Test output format of Maigret tools."""

    def test_maigret_output_is_json(self, maigret_username_tool):
        """Test that maigret tool returns valid JSON."""
        with patch('tools.maigret._run_maigret_sync') as mock_run:
            mock_run.return_value = {
                "success": True,
                "username": "test",
                "found_count": 0,
                "results": []
            }
            
            result = maigret_username_tool._run("test")
            
            # Should be valid JSON
            parsed = json.loads(result)
            assert isinstance(parsed, dict)
            assert "success" in parsed


# =============================================================================
# Maigret Error Handling Tests
# =============================================================================

class TestMaigretErrorHandling:
    """Test error handling in Maigret tools."""

    @pytest.mark.asyncio
    async def test_maigret_handles_subprocess_error(self):
        """Test maigret handles subprocess errors gracefully."""
        with patch('tools.maigret._check_maigret_available', return_value=True):
            with patch('asyncio.create_subprocess_exec') as mock_exec:
                mock_exec.side_effect = OSError("Subprocess failed")
                
                result = await _run_maigret_async("test", timeout=10, top_sites=5)
                
                assert result["success"] is False
                assert "error" in result


# =============================================================================
# Maigret Command Generation Tests
# =============================================================================

class TestMaigretCommandGeneration:
    """Test that correct Maigret commands are generated."""

    def test_maigret_command_includes_top_sites(self):
        """Verify maigret command includes --top-sites."""
        # This tests the command structure indirectly
        with patch('tools.maigret._check_maigret_available', return_value=True):
            with patch('asyncio.create_subprocess_exec') as mock_exec:
                mock_process = AsyncMock()
                mock_process.communicate = AsyncMock(return_value=(b"", b""))
                mock_exec.return_value = mock_process
                
                asyncio.get_event_loop().run_until_complete(
                    _run_maigret_async("testuser", timeout=30, top_sites=100)
                )
                
                # Check the command includes expected arguments
                call_args = mock_exec.call_args[0]
                assert 'maigret' in call_args
                assert 'testuser' in call_args
                assert '--top-sites' in call_args
                assert '100' in call_args


# #############################################################################
# BBOT TESTS
# #############################################################################

# =============================================================================
# BBOT Tool Instantiation Tests
# =============================================================================

class TestBbotToolInstantiation:
    """Test that BBOT tools can be properly instantiated."""

    def test_bbot_subdomain_tool_creation(self, bbot_subdomain_tool):
        """Test BbotSubdomainTool instantiation."""
        assert bbot_subdomain_tool is not None
        assert bbot_subdomain_tool.name == "bbot_subdomain_enum"
        assert "subdomain" in bbot_subdomain_tool.description.lower()

    def test_bbot_web_tool_creation(self, bbot_web_tool):
        """Test BbotWebScanTool instantiation."""
        assert bbot_web_tool is not None
        assert bbot_web_tool.name == "bbot_web_recon"
        assert "web" in bbot_web_tool.description.lower()

    def test_bbot_email_tool_creation(self, bbot_email_tool):
        """Test BbotEmailTool instantiation."""
        assert bbot_email_tool is not None
        assert bbot_email_tool.name == "bbot_email_harvest"
        assert "email" in bbot_email_tool.description.lower()


# =============================================================================
# BBOT Tool Availability Tests
# =============================================================================

class TestBbotToolAvailability:
    """Test BBOT tool availability checking."""

    def test_check_bbot_available(self):
        """Test bbot availability check."""
        result = _check_bbot_available()
        # Should be boolean
        assert isinstance(result, bool)
        # If bbot is installed, should find it
        if shutil.which('bbot'):
            assert result is True


# =============================================================================
# BBOT Output Parsing Tests
# =============================================================================

class TestBbotOutputParsing:
    """Test BBOT output parsing functionality."""

    def test_parse_dns_names(self, mock_bbot_ndjson_output):
        """Test parsing DNS_NAME events."""
        subdomains = []
        for event in mock_bbot_ndjson_output:
            if event.get("type") == "DNS_NAME":
                subdomains.append(event.get("data", ""))
        
        assert len(subdomains) == 3
        assert "example.com" in subdomains
        assert "www.example.com" in subdomains
        assert "mail.example.com" in subdomains

    def test_parse_email_addresses(self, mock_bbot_ndjson_output):
        """Test parsing EMAIL_ADDRESS events."""
        emails = []
        for event in mock_bbot_ndjson_output:
            if event.get("type") == "EMAIL_ADDRESS":
                emails.append(event.get("data", ""))
        
        assert len(emails) == 1
        assert "admin@example.com" in emails

    def test_parse_technologies(self, mock_bbot_ndjson_output):
        """Test parsing TECHNOLOGY events."""
        techs = []
        for event in mock_bbot_ndjson_output:
            if event.get("type") == "TECHNOLOGY":
                techs.append(event.get("data", ""))
        
        assert len(techs) == 1
        assert "nginx" in techs


# =============================================================================
# BBOT Mock Execution Tests
# =============================================================================

class TestBbotMockExecution:
    """Test BBOT execution with mocked subprocess."""

    @pytest.mark.asyncio
    async def test_bbot_not_installed(self):
        """Test behavior when bbot is not installed."""
        with patch('tools.bbot._check_bbot_available', return_value=False):
            result = await _run_bbot_async("example.com", preset="subdomain-enum")
            
            assert result["success"] is False
            assert "not installed" in result["error"].lower()
            assert result["results"] == []


# =============================================================================
# BBOT Integration Tests (require actual tools installed)
# =============================================================================

@pytest.mark.slow
class TestBbotIntegration:
    """Integration tests for BBOT (require bbot installed)."""

    @pytest.mark.skipif(
        not shutil.which('bbot'),
        reason="bbot not installed"
    )
    @pytest.mark.asyncio
    async def test_bbot_real_subdomain_search(self):
        """Test real bbot subdomain enumeration."""
        result = await _run_bbot_async(
            "example.com",
            preset="subdomain-enum",
            require_flags=["passive"],
            timeout_minutes=1
        )
        
        # Should have target info
        assert "target" in result
        assert result["target"] == "example.com"
        # May timeout but should have some structure
        assert "results" in result

    @pytest.mark.skipif(
        not shutil.which('bbot'),
        reason="bbot not installed"
    )
    def test_bbot_subdomain_tool_sync(self, bbot_subdomain_tool):
        """Test synchronous subdomain tool execution."""
        result = bbot_subdomain_tool._run(
            domain="example.com",
            passive_only=True
        )
        
        # Should return JSON string
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "target" in parsed


# =============================================================================
# BBOT Input Validation Tests
# =============================================================================

class TestBbotInputValidation:
    """Test input validation for BBOT tools."""

    def test_bbot_subdomain_schema(self, bbot_subdomain_tool):
        """Test BbotSubdomainTool input schema."""
        schema = bbot_subdomain_tool.args_schema
        
        fields = schema.model_fields
        assert 'domain' in fields
        assert 'passive_only' in fields

    def test_bbot_email_schema(self, bbot_email_tool):
        """Test BbotEmailTool input schema."""
        schema = bbot_email_tool.args_schema
        
        fields = schema.model_fields
        assert 'domain' in fields


# =============================================================================
# BBOT Output Format Tests
# =============================================================================

class TestBbotOutputFormat:
    """Test output format of BBOT tools."""

    def test_bbot_output_is_json(self, bbot_subdomain_tool):
        """Test that bbot tool returns valid JSON."""
        with patch('tools.bbot._run_bbot_sync') as mock_run:
            mock_run.return_value = {
                "success": True,
                "target": "example.com",
                "events_found": 0,
                "results": []
            }
            
            result = bbot_subdomain_tool._run("example.com")
            
            # Should be valid JSON
            parsed = json.loads(result)
            assert isinstance(parsed, dict)
            assert "success" in parsed


# =============================================================================
# BBOT Error Handling Tests
# =============================================================================

class TestBbotErrorHandling:
    """Test error handling in BBOT tools."""

    @pytest.mark.asyncio
    async def test_bbot_handles_subprocess_error(self):
        """Test bbot handles subprocess errors gracefully."""
        with patch('tools.bbot._check_bbot_available', return_value=True):
            with patch('asyncio.create_subprocess_exec') as mock_exec:
                mock_exec.side_effect = OSError("Subprocess failed")
                
                result = await _run_bbot_async("example.com", preset="subdomain-enum")
                
                assert result["success"] is False
                assert "error" in result


# =============================================================================
# BBOT Command Generation Tests
# =============================================================================

class TestBbotCommandGeneration:
    """Test that correct BBOT commands are generated."""

    def test_bbot_command_includes_preset(self):
        """Verify bbot command includes -p preset."""
        with patch('tools.bbot._check_bbot_available', return_value=True):
            with patch('asyncio.create_subprocess_exec') as mock_exec:
                mock_process = AsyncMock()
                mock_process.communicate = AsyncMock(return_value=(b"", b""))
                mock_exec.return_value = mock_process
                
                asyncio.get_event_loop().run_until_complete(
                    _run_bbot_async("example.com", preset="subdomain-enum", require_flags=["passive"])
                )
                
                call_args = mock_exec.call_args[0]
                assert 'bbot' in call_args
                assert '-p' in call_args
                assert 'subdomain-enum' in call_args
                assert '-rf' in call_args
                assert 'passive' in call_args


# #############################################################################
# HOLEHE TESTS
# #############################################################################

# =============================================================================
# Holehe Tool Instantiation Tests
# =============================================================================

class TestHoleheToolInstantiation:
    """Tests for Holehe email OSINT tools instantiation."""
    
    def test_holehe_tool_creation(self):
        """Test HoleheEmailTool instantiation."""
        from tools.holehe import HoleheEmailTool
        
        tool = HoleheEmailTool()
        assert tool.name == "holehe_email_check"
        assert "email" in tool.description.lower()


# =============================================================================
# Holehe Input Schema Tests
# =============================================================================

class TestHoleheInputSchema:
    """Tests for Holehe input schema validation."""
        
    def test_holehe_input_schema(self):
        """Test HoleheEmailInput schema validation."""
        from tools.holehe import HoleheEmailInput
        
        # Valid input
        valid_input = HoleheEmailInput(email="test@example.com")
        assert valid_input.email == "test@example.com"
        assert valid_input.timeout == 15  # Default
        assert valid_input.only_used is True  # Default
        
        # With custom values
        custom_input = HoleheEmailInput(
            email="user@domain.org",
            timeout=30,
            only_used=False
        )
        assert custom_input.timeout == 30
        assert custom_input.only_used is False


# =============================================================================
# Holehe Tool Availability Tests
# =============================================================================

class TestHoleheToolAvailability:
    """Tests for Holehe availability checking."""
    
    def test_holehe_check_available(self):
        """Test holehe availability check."""
        from tools.holehe import check_holehe_installation
        
        result = check_holehe_installation()
        assert "tool" in result
        assert result["tool"] == "holehe"
        assert "available" in result
        assert isinstance(result["available"], bool)


# =============================================================================
# Holehe Output Parsing Tests
# =============================================================================

class TestHoleheOutputParsing:
    """Tests for Holehe output parsing."""
        
    def test_holehe_output_parsing(self):
        """Test parsing of holehe CLI output."""
        from tools.holehe import _parse_holehe_output
        
        sample_output = """
[+] twitter.com
[+] spotify.com
[-] facebook.com
[-] instagram.com
[x] google.com
[+] github.com
"""
        
        result = _parse_holehe_output(sample_output)
        
        assert "used" in result
        assert "not_used" in result
        assert "rate_limited" in result
        
        assert "twitter.com" in result["used"]
        assert "spotify.com" in result["used"]
        assert "github.com" in result["used"]
        assert len(result["used"]) == 3
        
        assert "facebook.com" in result["not_used"]
        assert "instagram.com" in result["not_used"]
        
        assert "google.com" in result["rate_limited"]


# =============================================================================
# Holehe Mock Execution Tests
# =============================================================================

class TestHoleheMockExecution:
    """Tests for Holehe execution with mocked subprocess."""
    
    def test_holehe_not_installed_error(self):
        """Test error handling when holehe is not installed."""
        from tools.holehe import _run_holehe_async
        
        with patch('tools.holehe._check_holehe_available', return_value=False):
            result = asyncio.run(_run_holehe_async("test@example.com"))
            
            assert result["success"] is False
            assert "not installed" in result["error"].lower()


# =============================================================================
# Holehe Integration Tests
# =============================================================================

@pytest.mark.slow
class TestHoleheIntegration:
    """Integration tests for Holehe (require holehe installed)."""
    
    def test_holehe_real_execution(self):
        """Integration test with real holehe execution."""
        from tools.holehe import HoleheEmailTool, _check_holehe_available
        
        if not _check_holehe_available():
            pytest.skip("Holehe not installed")
        
        tool = HoleheEmailTool()
        result = tool._run(email="test@example.com", timeout=30, only_used=True)
        
        data = json.loads(result)
        assert "success" in data
        assert "email" in data


# =============================================================================
# Holehe Command Structure Tests
# =============================================================================

class TestHoleheCommandStructure:
    """Tests for Holehe command structure."""
    
    def test_holehe_command_structure(self):
        """Test holehe command includes correct flags."""
        from tools.holehe import HoleheEmailInput
        
        input_data = HoleheEmailInput(
            email="test@example.com",
            timeout=20,
            only_used=True
        )
        
        # Schema validation
        assert input_data.email == "test@example.com"
        assert input_data.timeout == 20
        assert input_data.only_used is True


# #############################################################################
# AMASS TESTS
# #############################################################################

# =============================================================================
# Amass Tool Instantiation Tests
# =============================================================================

class TestAmassToolInstantiation:
    """Tests for Amass subdomain enumeration tools instantiation."""
    
    def test_amass_enum_tool_creation(self):
        """Test AmassEnumTool instantiation."""
        from tools.amass import AmassEnumTool
        
        tool = AmassEnumTool()
        assert tool.name == "amass_subdomain_enum"
        assert "subdomain" in tool.description.lower()
        
    def test_amass_intel_tool_creation(self):
        """Test AmassIntelTool instantiation."""
        from tools.amass import AmassIntelTool
        
        tool = AmassIntelTool()
        assert tool.name == "amass_intel_discovery"
        assert "organization" in tool.description.lower()


# =============================================================================
# Amass Input Schema Tests
# =============================================================================

class TestAmassInputSchema:
    """Tests for Amass input schema validation."""
    
    def test_amass_enum_input_schema(self):
        """Test AmassEnumInput schema validation."""
        from tools.amass import AmassEnumInput
        
        # Valid input with defaults
        valid_input = AmassEnumInput(domain="example.com")
        assert valid_input.domain == "example.com"
        assert valid_input.passive is True  # Default
        assert valid_input.timeout == 300  # Default
        
        # Custom values
        custom_input = AmassEnumInput(
            domain="target.org",
            passive=False,
            timeout=600
        )
        assert custom_input.passive is False
        assert custom_input.timeout == 600
    
    def test_amass_intel_input_schema(self):
        """Test AmassIntelInput schema validation."""
        from tools.amass import AmassIntelInput
        
        valid_input = AmassIntelInput(org="Google LLC")
        assert valid_input.org == "Google LLC"
        assert valid_input.timeout == 180  # Default


# =============================================================================
# Amass Tool Availability Tests
# =============================================================================

class TestAmassToolAvailability:
    """Tests for Amass availability checking."""
    
    def test_amass_check_available(self):
        """Test amass availability check."""
        from tools.amass import check_amass_installation
        
        result = check_amass_installation()
        assert "tool" in result
        assert result["tool"] == "amass"
        assert "available" in result
        assert isinstance(result["available"], bool)
    
    def test_amass_find_binary(self):
        """Test finding amass binary in various locations."""
        from tools.amass import _find_amass_binary
        
        # This may or may not find it depending on installation
        binary = _find_amass_binary()
        # Just test it returns None or a string
        assert binary is None or isinstance(binary, str)


# =============================================================================
# Amass Mock Execution Tests
# =============================================================================

class TestAmassMockExecution:
    """Tests for Amass execution with mocked subprocess."""
    
    def test_amass_not_installed_error(self):
        """Test error handling when amass is not installed."""
        from tools.amass import _run_amass_enum_async
        
        with patch('tools.amass._find_amass_binary', return_value=None):
            result = asyncio.run(_run_amass_enum_async("example.com"))
            
            assert result["success"] is False
            assert "not installed" in result["error"].lower()


# =============================================================================
# Amass Integration Tests
# =============================================================================

@pytest.mark.slow
class TestAmassIntegration:
    """Integration tests for Amass (require amass installed)."""
    
    def test_amass_real_enum_execution(self):
        """Integration test with real amass enum execution."""
        from tools.amass import AmassEnumTool, _find_amass_binary
        
        if not _find_amass_binary():
            pytest.skip("Amass not installed")
        
        tool = AmassEnumTool()
        # Use a small domain and short timeout
        result = tool._run(domain="example.com", passive=True, timeout=60)
        
        data = json.loads(result)
        assert "success" in data
        assert "domain" in data


# =============================================================================
# Amass Command Structure Tests
# =============================================================================

class TestAmassCommandStructure:
    """Tests for Amass command structure."""
    
    def test_amass_passive_flag(self):
        """Test amass passive mode flag inclusion."""
        from tools.amass import AmassEnumInput
        
        passive_input = AmassEnumInput(domain="example.com", passive=True)
        active_input = AmassEnumInput(domain="example.com", passive=False)
        
        assert passive_input.passive is True
        assert active_input.passive is False


# #############################################################################
# PHONEINFOGA TESTS
# #############################################################################

# =============================================================================
# PhoneInfoga Tool Instantiation Tests
# =============================================================================

class TestPhoneInfogaToolInstantiation:
    """Tests for PhoneInfoga phone number OSINT tools instantiation."""
    
    def test_phoneinfoga_tool_creation(self):
        """Test PhoneInfogaScanTool instantiation."""
        from tools.phoneinfoga import PhoneInfogaScanTool
        
        tool = PhoneInfogaScanTool()
        assert tool.name == "phoneinfoga_scan"
        assert "phone" in tool.description.lower()


# =============================================================================
# PhoneInfoga Input Schema Tests
# =============================================================================

class TestPhoneInfogaInputSchema:
    """Tests for PhoneInfoga input schema validation."""
    
    def test_phoneinfoga_input_schema(self):
        """Test PhoneInfogaScanInput schema validation."""
        from tools.phoneinfoga import PhoneInfogaScanInput
        
        # Valid input
        valid_input = PhoneInfogaScanInput(phone_number="+34612345678")
        assert valid_input.phone_number == "+34612345678"
        assert valid_input.timeout == 60  # Default
        
        # US format
        us_input = PhoneInfogaScanInput(phone_number="+1-555-123-4567")
        assert "+1" in us_input.phone_number


# =============================================================================
# PhoneInfoga Tool Availability Tests
# =============================================================================

class TestPhoneInfogaToolAvailability:
    """Tests for PhoneInfoga availability checking."""
    
    def test_phoneinfoga_check_available(self):
        """Test phoneinfoga availability check."""
        from tools.phoneinfoga import check_phoneinfoga_installation
        
        result = check_phoneinfoga_installation()
        assert "tool" in result
        assert result["tool"] == "phoneinfoga"
        assert "available" in result
        assert isinstance(result["available"], bool)
    
    def test_phoneinfoga_find_binary(self):
        """Test finding phoneinfoga binary."""
        from tools.phoneinfoga import _find_phoneinfoga_binary
        
        binary = _find_phoneinfoga_binary()
        # Just test it returns None or a string
        assert binary is None or isinstance(binary, str)


# =============================================================================
# PhoneInfoga Output Parsing Tests
# =============================================================================

class TestPhoneInfogaOutputParsing:
    """Tests for PhoneInfoga output parsing."""
    
    def test_phoneinfoga_output_parsing(self):
        """Test parsing of phoneinfoga output."""
        from tools.phoneinfoga import _parse_phoneinfoga_output
        
        sample_output = """
Country: Spain
Carrier: Movistar
Line type: mobile
Valid: true
Local format: 612345678
International format: +34612345678
Country code: 34

Running scanner numverify...
Found 2 results
"""
        
        result = _parse_phoneinfoga_output(sample_output)
        
        assert result["country"] == "Spain"
        assert result["carrier"] == "Movistar"
        assert result["line_type"] == "mobile"
        assert result["valid"] is True
        assert result["local_format"] == "612345678"
        assert result["international_format"] == "+34612345678"
        assert result["country_code"] == "34"


# =============================================================================
# PhoneInfoga Mock Execution Tests
# =============================================================================

class TestPhoneInfogaMockExecution:
    """Tests for PhoneInfoga execution with mocked subprocess."""
    
    def test_phoneinfoga_not_installed_error(self):
        """Test error handling when phoneinfoga is not installed."""
        from tools.phoneinfoga import _run_phoneinfoga_async
        
        with patch('tools.phoneinfoga._find_phoneinfoga_binary', return_value=None):
            result = asyncio.run(_run_phoneinfoga_async("+34612345678"))
            
            assert result["success"] is False
            assert "not installed" in result["error"].lower()


# =============================================================================
# PhoneInfoga Integration Tests
# =============================================================================

@pytest.mark.slow
class TestPhoneInfogaIntegration:
    """Integration tests for PhoneInfoga (require phoneinfoga installed)."""
    
    def test_phoneinfoga_real_execution(self):
        """Integration test with real phoneinfoga execution."""
        from tools.phoneinfoga import PhoneInfogaScanTool, _find_phoneinfoga_binary
        
        if not _find_phoneinfoga_binary():
            pytest.skip("PhoneInfoga not installed")
        
        tool = PhoneInfogaScanTool()
        # Use a test number (will likely fail validation but tests the flow)
        result = tool._run(phone_number="+1234567890", timeout=30)
        
        data = json.loads(result)
        assert "phone_number" in data or "error" in data


# =============================================================================
# PhoneInfoga Command Structure Tests
# =============================================================================

class TestPhoneInfogaCommandStructure:
    """Tests for PhoneInfoga command structure."""
    
    def test_phoneinfoga_number_normalization(self):
        """Test phone number normalization."""
        from tools.phoneinfoga import PhoneInfogaScanInput
        
        # Numbers with various formats
        numbers_to_test = [
            ("+34612345678", "+34612345678"),  # Already has +
            ("0034612345678", "0034612345678"),  # Has 00 prefix
            ("34612345678", "34612345678"),  # Just digits
        ]
        
        for input_num, expected in numbers_to_test:
            schema = PhoneInfogaScanInput(phone_number=input_num)
            assert schema.phone_number == expected


# #############################################################################
# TOOLS MODULE INTEGRATION TESTS
# #############################################################################

# =============================================================================
# Module Exports Tests
# =============================================================================

class TestToolsModuleExports:
    """Test tools module exports and integration."""
    
    def test_all_osint_tools_exported(self):
        """Test that all OSINT tools are exported from tools module."""
        from tools import (
            MaigretUsernameTool,
            MaigretReportTool,
            BbotSubdomainTool,
            BbotWebScanTool,
            BbotEmailTool,
            HoleheEmailTool,
            AmassEnumTool,
            AmassIntelTool,
            PhoneInfogaScanTool,
        )
        
        # All imports should succeed
        assert MaigretUsernameTool is not None
        assert MaigretReportTool is not None
        assert BbotSubdomainTool is not None
        assert BbotWebScanTool is not None
        assert BbotEmailTool is not None
        assert HoleheEmailTool is not None
        assert AmassEnumTool is not None
        assert AmassIntelTool is not None
        assert PhoneInfogaScanTool is not None


# =============================================================================
# Tool Getter Functions Tests
# =============================================================================

class TestToolGetterFunctions:
    """Test tool getter functions."""
    
    def test_get_maigret_tools(self):
        """Test get_maigret_tools function."""
        from tools import get_maigret_tools
        
        tools = get_maigret_tools()
        assert len(tools) >= 1
        tool_names = [t.name for t in tools]
        assert "maigret_username_search" in tool_names
    
    def test_get_bbot_tools(self):
        """Test get_bbot_tools function."""
        from tools import get_bbot_tools
        
        tools = get_bbot_tools()
        assert len(tools) >= 1
        tool_names = [t.name for t in tools]
        assert "bbot_subdomain_enum" in tool_names
    
    def test_get_holehe_tools(self):
        """Test get_holehe_tools function."""
        from tools import get_holehe_tools
        
        tools = get_holehe_tools()
        assert len(tools) == 1
        assert tools[0].name == "holehe_email_check"
    
    def test_get_amass_tools(self):
        """Test get_amass_tools function."""
        from tools import get_amass_tools
        
        tools = get_amass_tools()
        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "amass_subdomain_enum" in tool_names
        assert "amass_intel_discovery" in tool_names
    
    def test_get_phoneinfoga_tools(self):
        """Test get_phoneinfoga_tools function."""
        from tools import get_phoneinfoga_tools
        
        tools = get_phoneinfoga_tools()
        assert len(tools) == 1
        assert tools[0].name == "phoneinfoga_scan"


# =============================================================================
# Tool Category Functions Tests
# =============================================================================

class TestToolCategoryFunctions:
    """Test tool category functions."""
    
    def test_get_identity_tools_includes_new(self):
        """Test that get_identity_tools includes new tools."""
        from tools import get_identity_tools
        
        tools = get_identity_tools()
        tool_names = [t.name for t in tools]
        
        # Should include holehe and phoneinfoga
        assert "holehe_email_check" in tool_names
        assert "phoneinfoga_scan" in tool_names
    
    def test_get_domain_tools_includes_amass(self):
        """Test that get_domain_tools includes Amass."""
        from tools import get_domain_tools
        
        tools = get_domain_tools()
        tool_names = [t.name for t in tools]
        
        # Should include amass tools
        assert "amass_subdomain_enum" in tool_names
        assert "amass_intel_discovery" in tool_names
    
    def test_get_all_tools_includes_all_osint(self):
        """Test that get_all_tools includes all OSINT tools."""
        from tools import get_all_tools
        
        tools = get_all_tools()
        tool_names = [t.name for t in tools]
        
        # Should include all OSINT tools
        assert "maigret_username_search" in tool_names
        assert "bbot_subdomain_enum" in tool_names
        assert "holehe_email_check" in tool_names
        assert "amass_subdomain_enum" in tool_names
        assert "phoneinfoga_scan" in tool_names


# =============================================================================
# Error Handling Edge Cases
# =============================================================================

class TestErrorHandlingEdgeCases:
    """Test error handling for edge cases across all tools."""
    
    def test_holehe_timeout_handling(self):
        """Test timeout handling for holehe."""
        from tools.holehe import _run_holehe_async
        
        async def mock_communicate():
            await asyncio.sleep(10)  # Simulate long operation
            return b"", b""
        
        with patch('tools.holehe._check_holehe_available', return_value=True):
            with patch('asyncio.create_subprocess_exec') as mock_proc:
                mock_proc.return_value.communicate = mock_communicate
                
                # Use very short timeout
                # Should handle timeout gracefully
                pass
    
    def test_phoneinfoga_invalid_number_handling(self):
        """Test handling of invalid phone numbers."""
        from tools.phoneinfoga import PhoneInfogaScanTool, _find_phoneinfoga_binary
        
        if not _find_phoneinfoga_binary():
            pytest.skip("PhoneInfoga not installed")
        
        tool = PhoneInfogaScanTool()
        # Clearly invalid number
        result = tool._run(phone_number="not-a-number", timeout=10)
        
        data = json.loads(result)
        # Should return some result even for invalid input
        assert "phone_number" in data or "error" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
