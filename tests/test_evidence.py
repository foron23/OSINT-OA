# =============================================================================
# Evidence Extraction Tests
# =============================================================================
"""
Tests for evidence extraction functionality in agents.

Tests the new evidence collection, IOC extraction, and confidence scoring
capabilities added to the agent base class.

Run with: pytest tests/test_evidence.py -v
"""

import pytest
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import LangChainAgent, AgentCapabilities
from agents.osint import TavilySearchAgent, IOCAnalysisAgent, ThreatIntelAgent


class TestEvidenceExtraction:
    """Test evidence extraction from agent results."""
    
    def test_extract_ip_addresses(self):
        """Test IP address extraction from result text."""
        agent = TavilySearchAgent()
        result = """
        The malicious server was found at 192.168.1.100 and also at 10.0.0.1.
        Additional C2 infrastructure includes 203.0.113.50.
        """
        evidence = agent._extract_evidence_from_result(result)
        
        ip_values = [e["value"] for e in evidence if e.get("ioc_type") == "ip"]
        assert "192.168.1.100" in ip_values
        assert "10.0.0.1" in ip_values
        assert "203.0.113.50" in ip_values
    
    def test_extract_domains(self):
        """Test domain extraction from result text."""
        agent = TavilySearchAgent()
        result = """
        The phishing campaign used malware.evil.io and attack-server.net
        to distribute payloads.
        """
        evidence = agent._extract_evidence_from_result(result)
        
        domain_values = [e["value"] for e in evidence if e.get("ioc_type") == "domain"]
        assert "malware.evil.io" in domain_values
        assert "attack-server.net" in domain_values
    
    def test_extract_hashes(self):
        """Test hash extraction (MD5, SHA1, SHA256)."""
        agent = TavilySearchAgent()
        result = """
        MD5: d41d8cd98f00b204e9800998ecf8427e
        SHA1: da39a3ee5e6b4b0d3255bfef95601890afd80709
        SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        """
        evidence = agent._extract_evidence_from_result(result)
        
        hash_values = [e["value"] for e in evidence if e.get("ioc_type") == "hash"]
        assert "d41d8cd98f00b204e9800998ecf8427e" in hash_values
        assert "da39a3ee5e6b4b0d3255bfef95601890afd80709" in hash_values
        assert "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" in hash_values
    
    def test_extract_cve(self):
        """Test CVE identifier extraction."""
        agent = TavilySearchAgent()
        result = """
        The vulnerability CVE-2024-21762 was exploited along with CVE-2023-44487.
        """
        evidence = agent._extract_evidence_from_result(result)
        
        cve_values = [e["value"] for e in evidence if e.get("ioc_type") == "cve"]
        assert "CVE-2024-21762" in cve_values
        assert "CVE-2023-44487" in cve_values
    
    def test_extract_emails(self):
        """Test email address extraction."""
        agent = TavilySearchAgent()
        result = """
        Contact attacker@malware.io for ransom. 
        Legitimate contact: support@company.com
        """
        evidence = agent._extract_evidence_from_result(result)
        
        email_values = [e["value"] for e in evidence if e.get("ioc_type") == "email"]
        assert "attacker@malware.io" in email_values
        assert "support@company.com" in email_values
    
    def test_extract_urls(self):
        """Test URL extraction."""
        agent = TavilySearchAgent()
        result = """
        Payload downloaded from https://malware.evil.com/payload.exe
        and https://attack.net/stage2.dll
        """
        evidence = agent._extract_evidence_from_result(result)
        
        url_values = [e["value"] for e in evidence if e.get("ioc_type") == "url"]
        assert any("malware.evil.com" in url for url in url_values)
        assert any("attack.net" in url for url in url_values)
    
    def test_extract_structured_json_evidence(self):
        """Test extraction from structured JSON response."""
        agent = TavilySearchAgent()
        result = '''
        Here are my findings:
        ```json
        {
          "summary": "Test investigation",
          "evidence": {
            "iocs": [
              {"type": "ip", "value": "1.2.3.4", "context": "C2 server"},
              {"type": "domain", "value": "test-malware.net", "context": "Distribution"}
            ],
            "entities": [
              {"type": "threat_actor", "name": "APT28", "context": "Attribution"}
            ],
            "techniques": ["T1566", "T1059.001"]
          },
          "confidence_score": 0.85
        }
        ```
        '''
        evidence = agent._extract_evidence_from_result(result)
        
        # Check IOCs from JSON were extracted
        ioc_values = [e["value"] for e in evidence if e.get("type") == "ioc"]
        assert "1.2.3.4" in ioc_values
        assert "test-malware.net" in ioc_values
        
        # Check entities were extracted
        entities = [e for e in evidence if e.get("type") == "entity"]
        assert any(e.get("name") == "APT28" for e in entities)
        
        # Check techniques were extracted
        techniques = [e for e in evidence if e.get("type") == "technique"]
        assert any(e.get("mitre_id") == "T1566" for e in techniques)
    
    def test_no_duplicate_evidence(self):
        """Test that duplicate IOCs are not extracted."""
        agent = TavilySearchAgent()
        result = """
        The IP 192.168.1.1 was seen multiple times.
        Server at 192.168.1.1 is confirmed malicious.
        Again 192.168.1.1 appears in logs.
        """
        evidence = agent._extract_evidence_from_result(result)
        
        ip_occurrences = [e for e in evidence if e.get("value") == "192.168.1.1"]
        assert len(ip_occurrences) == 1
    
    def test_filters_false_positive_domains(self):
        """Test that common false positive domains are filtered."""
        agent = TavilySearchAgent()
        result = """
        The report mentions google.com and example.com as references.
        Real malicious domain: attacker-server.net
        """
        evidence = agent._extract_evidence_from_result(result)
        
        domain_values = [e["value"] for e in evidence if e.get("ioc_type") == "domain"]
        assert "google.com" not in domain_values
        assert "example.com" not in domain_values
        assert "attacker-server.net" in domain_values


class TestConfidenceScoring:
    """Test confidence score calculation."""
    
    def test_base_confidence(self):
        """Test that empty results get base confidence."""
        agent = TavilySearchAgent()
        result = "No specific findings."
        evidence = []
        
        confidence = agent._calculate_confidence(result, evidence)
        
        assert confidence >= 0.3
        assert confidence <= 1.0
    
    def test_evidence_boosts_confidence(self):
        """Test that having evidence boosts confidence."""
        agent = TavilySearchAgent()
        result = "Found malicious IP: 192.168.1.1"
        evidence = [
            {"type": "ioc", "ioc_type": "ip", "value": "192.168.1.1"},
            {"type": "ioc", "ioc_type": "domain", "value": "test.net"},
        ]
        
        confidence = agent._calculate_confidence(result, evidence)
        
        # Should be higher than base
        assert confidence > 0.3
    
    def test_sources_boost_confidence(self):
        """Test that having source URLs boosts confidence."""
        agent = TavilySearchAgent()
        result = """
        Found at https://source1.com/report and https://source2.com/analysis
        and also https://source3.org/data
        """
        evidence = []
        
        confidence = agent._calculate_confidence(result, evidence)
        
        # Should be boosted by sources
        assert confidence > 0.3
    
    def test_structured_json_uses_reported_confidence(self):
        """Test that structured JSON confidence is used when available."""
        agent = TavilySearchAgent()
        result = '''
        ```json
        {
          "summary": "Test",
          "confidence_score": 0.95
        }
        ```
        '''
        evidence = []
        
        confidence = agent._calculate_confidence(result, evidence)
        
        assert confidence == 0.95
    
    def test_confidence_never_exceeds_one(self):
        """Test that confidence score never exceeds 1.0."""
        agent = TavilySearchAgent()
        result = """
        Many sources: http://a.com http://b.com http://c.com http://d.com 
        http://e.com http://f.com http://g.com http://h.com http://i.com http://j.com
        ```json
        {"confidence_score": 1.5}
        ```
        """
        evidence = [{"type": "ioc"} for _ in range(20)]
        
        confidence = agent._calculate_confidence(result, evidence)
        
        assert confidence <= 1.0


class TestAgentSystemPrompts:
    """Test that agent system prompts contain required elements."""
    
    def test_prompt_contains_evidence_instructions(self):
        """Test that prompts instruct agents to collect evidence."""
        agent = TavilySearchAgent()
        prompt = agent._get_system_prompt()
        
        # Should mention IOCs
        assert "IOC" in prompt or "ioc" in prompt.lower() or "indicator" in prompt.lower()
        
        # Should mention structured output
        assert "json" in prompt.lower() or "JSON" in prompt
    
    def test_threat_intel_prompt_has_mitre_attack(self):
        """Test that ThreatIntelAgent prompt mentions MITRE ATT&CK."""
        agent = ThreatIntelAgent()
        prompt = agent._get_system_prompt()
        
        assert "MITRE" in prompt or "ATT&CK" in prompt
    
    def test_ioc_agent_prompt_comprehensive(self):
        """Test that IOCAnalysisAgent prompt covers all IOC types."""
        agent = IOCAnalysisAgent()
        prompt = agent._get_system_prompt()
        
        # Should mention various IOC types
        assert "IP" in prompt or "ip" in prompt.lower()
        assert "domain" in prompt.lower()
        assert "hash" in prompt.lower()
        assert "CVE" in prompt or "cve" in prompt.lower()
    
    def test_prompts_mention_collaboration(self):
        """Test that prompts mention multi-agent collaboration."""
        agents = [TavilySearchAgent(), IOCAnalysisAgent(), ThreatIntelAgent()]
        
        for agent in agents:
            prompt = agent._get_system_prompt()
            # Should mention collaboration/team/multi-agent
            collaboration_terms = ["collaborat", "team", "multi-agent", "investigation"]
            has_collaboration = any(term in prompt.lower() for term in collaboration_terms)
            assert has_collaboration, f"{agent.name} prompt should mention collaboration"


class TestTracingIntegration:
    """Test tracing integration with agents."""
    
    def test_tracing_context_available(self):
        """Test that TracingContext can be imported and used."""
        from agents.tracing import TracingContext, TraceType
        
        assert TracingContext is not None
        assert TraceType is not None
    
    def test_trace_types_exist(self):
        """Test that all trace types are defined."""
        from agents.tracing import TraceType
        
        assert hasattr(TraceType, 'TOOL_CALL')
        assert hasattr(TraceType, 'AGENT_ACTION')
        assert hasattr(TraceType, 'LLM_REASONING')
        assert hasattr(TraceType, 'DECISION')
        assert hasattr(TraceType, 'CHECKPOINT')
    
    def test_trace_repository_methods(self):
        """Test that TraceRepository has required methods."""
        from db import TraceRepository
        
        assert hasattr(TraceRepository, 'start_trace')
        assert hasattr(TraceRepository, 'complete_trace')
        assert hasattr(TraceRepository, 'fail_trace')
        assert hasattr(TraceRepository, 'get_by_run_id')
        assert hasattr(TraceRepository, 'get_evidence_summary')


class TestEvidenceOutputFormat:
    """Test that agents can parse various evidence formats."""
    
    def test_parse_findings_with_sources(self):
        """Test parsing findings with source URLs."""
        agent = TavilySearchAgent()
        result = '''
        ```json
        {
          "findings": [
            {
              "title": "Ransomware Attack",
              "description": "New variant detected",
              "source_url": "https://threat-intel.com/report",
              "confidence": 0.9
            }
          ],
          "sources": ["https://threat-intel.com/report"]
        }
        ```
        '''
        evidence = agent._extract_evidence_from_result(result)
        
        sources = [e for e in evidence if e.get("type") == "source"]
        assert len(sources) > 0
    
    def test_mixed_regex_and_json_extraction(self):
        """Test that both regex and JSON extraction work together."""
        agent = TavilySearchAgent()
        result = '''
        Additional IOC found: 8.8.8.8
        
        ```json
        {
          "evidence": {
            "iocs": [
              {"type": "ip", "value": "1.1.1.1", "context": "DNS"}
            ]
          }
        }
        ```
        
        Also CVE-2024-12345 was mentioned.
        '''
        evidence = agent._extract_evidence_from_result(result)
        
        # Should find IOCs from both regex and JSON
        values = [e.get("value") for e in evidence]
        assert "8.8.8.8" in values  # From regex
        assert "1.1.1.1" in values  # From JSON
        assert "CVE-2024-12345" in values  # From regex
