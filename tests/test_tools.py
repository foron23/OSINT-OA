# =============================================================================
# Tool Tests - Functionality and Behavior
# =============================================================================
"""
Tests for tool functionality and behavior.

These tests verify that tools work correctly with valid inputs.
Note: Some tools require API keys or network access.

Run with: pytest tests/test_tools.py -v
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.base import UrlInput, WebSearchInput, TextAnalysisInput
from tools.search import TavilySearchTool, DuckDuckGoSearchTool
from tools.scraping import WebScraperTool, GoogleDorkBuilderTool
from tools.analysis import IOCExtractorTool, TagExtractorTool
from tools.maigret import (
    MaigretUsernameTool,
    MaigretReportTool,
)
from tools.bbot import (
    BbotSubdomainTool,
    BbotWebScanTool,
    BbotEmailTool,
)
from tools.telegram import (
    TelegramMCPSendTool,
    TelegramMCPPublishReportTool,
    TelegramMCPListDialogsTool,
)


class TestToolInstantiation:
    """Test that all tools can be instantiated."""
    
    def test_tavily_search_tool(self):
        """Test TavilySearchTool instantiation."""
        tool = TavilySearchTool()
        assert tool is not None
        assert tool.name == "tavily_search"
    
    def test_duckduckgo_search_tool(self):
        """Test DuckDuckGoSearchTool instantiation."""
        tool = DuckDuckGoSearchTool()
        assert tool is not None
        assert tool.name == "duckduckgo_search"
    
    def test_web_scraper_tool(self):
        """Test WebScraperTool instantiation."""
        tool = WebScraperTool()
        assert tool is not None
        assert tool.name == "web_scraper"
    
    def test_google_dork_builder_tool(self):
        """Test GoogleDorkBuilderTool instantiation."""
        tool = GoogleDorkBuilderTool()
        assert tool is not None
        assert tool.name == "google_dork_builder"
    
    def test_ioc_extractor_tool(self):
        """Test IOCExtractorTool instantiation."""
        tool = IOCExtractorTool()
        assert tool is not None
        assert tool.name == "ioc_extractor"
    
    def test_tag_extractor_tool(self):
        """Test TagExtractorTool instantiation."""
        tool = TagExtractorTool()
        assert tool is not None
        assert tool.name == "tag_extractor"
    
    def test_maigret_username_tool(self):
        """Test MaigretUsernameTool instantiation."""
        tool = MaigretUsernameTool()
        assert tool is not None
        assert tool.name == "maigret_username_search"
    
    def test_maigret_report_tool(self):
        """Test MaigretReportTool instantiation."""
        tool = MaigretReportTool()
        assert tool is not None
        assert tool.name == "maigret_report"
    
    def test_bbot_subdomain_tool(self):
        """Test BbotSubdomainTool instantiation."""
        tool = BbotSubdomainTool()
        assert tool is not None
        assert tool.name == "bbot_subdomain_enum"
    
    def test_bbot_web_scan_tool(self):
        """Test BbotWebScanTool instantiation."""
        tool = BbotWebScanTool()
        assert tool is not None
        assert tool.name == "bbot_web_recon"
    
    def test_bbot_email_tool(self):
        """Test BbotEmailTool instantiation."""
        tool = BbotEmailTool()
        assert tool is not None
        assert tool.name == "bbot_email_harvest"
    
    def test_telegram_send_tool(self):
        """Test TelegramMCPSendTool instantiation."""
        tool = TelegramMCPSendTool()
        assert tool is not None
        assert tool.name == "telegram_mcp_send"
    
    def test_telegram_publish_tool(self):
        """Test TelegramMCPPublishReportTool instantiation."""
        tool = TelegramMCPPublishReportTool()
        assert tool is not None
        assert tool.name == "telegram_mcp_publish_report"
    
    def test_telegram_list_dialogs_tool(self):
        """Test TelegramMCPListDialogsTool instantiation."""
        tool = TelegramMCPListDialogsTool()
        assert tool is not None
        assert tool.name == "telegram_mcp_list_dialogs"


class TestToolMetadata:
    """Test tool metadata and descriptions."""
    
    def test_tools_have_descriptions(self):
        """Test all tools have descriptions."""
        tools = [
            TavilySearchTool(),
            DuckDuckGoSearchTool(),
            WebScraperTool(),
            GoogleDorkBuilderTool(),
            IOCExtractorTool(),
            TagExtractorTool(),
            MaigretUsernameTool(),
            MaigretReportTool(),
            BbotSubdomainTool(),
            TelegramMCPSendTool(),
        ]
        
        for tool in tools:
            assert tool.description is not None
            assert len(tool.description) > 10
    
    def test_tools_have_args_schema(self):
        """Test tools have input schemas."""
        tools = [
            TavilySearchTool(),
            DuckDuckGoSearchTool(),
            WebScraperTool(),
            IOCExtractorTool(),
        ]
        
        for tool in tools:
            assert hasattr(tool, 'args_schema') or hasattr(tool, 'args')


class TestIOCExtractor:
    """Test IOC extraction functionality."""
    
    def test_extract_ipv4(self):
        """Test IPv4 extraction."""
        tool = IOCExtractorTool()
        text = "The attacker used IP 192.168.1.100 to connect."
        result = tool._run(text)
        
        assert "192.168.1.100" in result
    
    def test_extract_domain(self):
        """Test domain extraction."""
        tool = IOCExtractorTool()
        text = "Malware connected to malicious-domain.com for C2."
        result = tool._run(text)
        
        assert "malicious-domain.com" in result
    
    def test_extract_email(self):
        """Test email extraction."""
        tool = IOCExtractorTool()
        text = "Phishing email from attacker@evil.com was detected."
        result = tool._run(text)
        
        assert "attacker@evil.com" in result
    
    def test_extract_hash_md5(self):
        """Test MD5 hash extraction."""
        tool = IOCExtractorTool()
        text = "File hash: d41d8cd98f00b204e9800998ecf8427e"
        result = tool._run(text)
        
        assert "d41d8cd98f00b204e9800998ecf8427e" in result
    
    def test_extract_hash_sha256(self):
        """Test SHA256 hash extraction."""
        tool = IOCExtractorTool()
        text = "SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        result = tool._run(text)
        
        assert "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" in result
    
    def test_extract_cve(self):
        """Test CVE extraction."""
        tool = IOCExtractorTool()
        text = "Vulnerability CVE-2024-12345 was exploited."
        result = tool._run(text)
        
        assert "CVE-2024-12345" in result
    
    def test_extract_url(self):
        """Test URL extraction."""
        tool = IOCExtractorTool()
        text = "Malware downloaded from https://evil.com/malware.exe"
        result = tool._run(text)
        
        assert "https://evil.com/malware.exe" in result
    
    def test_empty_text(self):
        """Test with empty text."""
        tool = IOCExtractorTool()
        result = tool._run("")
        
        # Should not crash, return valid JSON
        assert result is not None


class TestGoogleDorkBuilder:
    """Test Google Dork builder functionality."""
    
    def test_build_dork_query(self):
        """Test building dork query."""
        tool = GoogleDorkBuilderTool()
        result = tool._run("password filetype:pdf")
        
        assert result is not None
        assert "site:" in result or "filetype:" in result or "password" in result
    
    def test_dork_templates_exist(self):
        """Test dork templates are defined."""
        assert hasattr(GoogleDorkBuilderTool, 'DORK_TEMPLATES')
        templates = GoogleDorkBuilderTool.DORK_TEMPLATES
        
        assert isinstance(templates, dict)
        assert len(templates) > 0


class TestTagExtractor:
    """Test tag extraction functionality."""
    
    def test_extract_security_tags(self):
        """Test security-related tag extraction."""
        tool = TagExtractorTool()
        text = "This ransomware attack exploited a vulnerability in the firewall."
        result = tool._run(text)
        
        # Should identify security-related content
        assert result is not None
    
    def test_extract_tech_tags(self):
        """Test technology tag extraction."""
        tool = TagExtractorTool()
        text = "The Python application uses Flask and PostgreSQL database."
        result = tool._run(text)
        
        assert result is not None


class TestToolBase:
    """Test base tool classes and data structures."""
    
    def test_url_input_validation(self):
        """Test UrlInput validation."""
        input_data = UrlInput(url="https://example.com")
        assert input_data.url == "https://example.com"
    
    def test_web_search_input_validation(self):
        """Test WebSearchInput validation."""
        input_data = WebSearchInput(query="test query")
        assert input_data.query == "test query"
        assert input_data.max_results == 10  # default
    
    def test_text_analysis_input_validation(self):
        """Test TextAnalysisInput validation."""
        input_data = TextAnalysisInput(text="sample text")
        assert input_data.text == "sample text"


class TestToolsIntegration:
    """Integration tests for tools (may require network/API keys)."""
    
    @pytest.mark.skip(reason="Requires network access")
    def test_duckduckgo_search_real(self):
        """Test real DuckDuckGo search."""
        tool = DuckDuckGoSearchTool()
        result = tool._run("Python programming")
        
        assert result is not None
        assert len(result) > 0
    
    @pytest.mark.skip(reason="Requires TAVILY_API_KEY")
    def test_tavily_search_real(self):
        """Test real Tavily search."""
        tool = TavilySearchTool()
        result = tool._run("cybersecurity news")
        
        assert result is not None
    
    @pytest.mark.skip(reason="Requires network access")
    def test_web_scraper_real(self):
        """Test real web scraping."""
        tool = WebScraperTool()
        result = tool._run("https://example.com")
        
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
