# =============================================================================
# OSINT Agentic Operations - Analysis Tools
# =============================================================================
"""
Text analysis and extraction tools for OSINT investigations.

Provides:
- IOCExtractorTool: Extract Indicators of Compromise from text
- TagExtractorTool: Extract relevant tags/keywords from text

These tools are used by agents to extract evidence and IOCs from content.
"""

import re
import json
import logging
from typing import Optional, Type, List, Dict, Any
from collections import Counter

from pydantic import BaseModel

from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun

from tools.base import TextAnalysisInput

logger = logging.getLogger(__name__)


# =============================================================================
# IOC Patterns
# =============================================================================

IOC_PATTERNS = {
    'ip': r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
    'domain': r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b',
    'url': r'https?://[^\s<>"{}|\\^`\[\]]+',
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'md5': r'\b[a-fA-F0-9]{32}\b',
    'sha1': r'\b[a-fA-F0-9]{40}\b',
    'sha256': r'\b[a-fA-F0-9]{64}\b',
    'cve': r'\bCVE-\d{4}-\d{4,7}\b',
    'btc': r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b',
    'eth': r'\b0x[a-fA-F0-9]{40}\b',
}

# Common false positive domains to filter
FALSE_POSITIVE_DOMAINS = {
    'example.com', 'example.org', 'example.net',
    'localhost', 'test.com', 'domain.com',
    'google.com', 'facebook.com', 'twitter.com',  # Too generic
    'github.com', 'githubusercontent.com',
}


class IOCExtractorTool(BaseTool):
    """
    Indicator of Compromise (IOC) extraction tool.
    
    Extracts security-relevant indicators from text:
    - IP addresses
    - Domains
    - URLs
    - Email addresses
    - Hashes (MD5, SHA1, SHA256)
    - CVE identifiers
    - Cryptocurrency addresses
    """
    
    name: str = "ioc_extractor"
    description: str = """Extract Indicators of Compromise (IOCs) from text.
    Finds: IPs, domains, URLs, emails, hashes (MD5/SHA1/SHA256), CVEs.
    Returns structured list of IOCs with type and value."""
    args_schema: Type[BaseModel] = TextAnalysisInput
    
    def _run(
        self,
        text: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Extract IOCs from text."""
        indicators = []
        seen = set()
        
        for ioc_type, pattern in IOC_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Normalize
                value = match.lower() if ioc_type != 'cve' else match.upper()
                
                # Skip duplicates
                key = f"{ioc_type}:{value}"
                if key in seen:
                    continue
                seen.add(key)
                
                # Skip false positives for domains
                if ioc_type == 'domain' and value in FALSE_POSITIVE_DOMAINS:
                    continue
                
                # Determine hash type
                if ioc_type in ('md5', 'sha1', 'sha256'):
                    actual_type = 'hash'
                    subtype = ioc_type
                else:
                    actual_type = ioc_type
                    subtype = None
                
                indicator = {
                    "type": actual_type,
                    "value": value,
                }
                if subtype:
                    indicator["subtype"] = subtype
                
                indicators.append(indicator)
        
        return json.dumps({
            "count": len(indicators),
            "indicators": indicators
        })
    
    async def _arun(
        self,
        text: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Async version of IOC extraction."""
        return self._run(text, run_manager)


# =============================================================================
# Tag Extraction
# =============================================================================

# OSINT-relevant tag categories
TAG_KEYWORDS = {
    'threat_type': [
        'ransomware', 'malware', 'phishing', 'apt', 'trojan', 'backdoor',
        'botnet', 'exploit', 'vulnerability', 'zero-day', 'ddos', 'spam'
    ],
    'threat_actor': [
        'lazarus', 'apt28', 'apt29', 'fancy bear', 'cozy bear', 'ta505',
        'revil', 'conti', 'lockbit', 'blackcat', 'alphv', 'scattered spider'
    ],
    'sector': [
        'healthcare', 'financial', 'government', 'education', 'energy',
        'manufacturing', 'retail', 'telecommunications', 'transportation'
    ],
    'attack_vector': [
        'spearphishing', 'watering hole', 'supply chain', 'credential stuffing',
        'brute force', 'social engineering', 'drive-by download'
    ],
    'region': [
        'russia', 'china', 'north korea', 'iran', 'usa', 'europe', 'asia'
    ]
}


class TagExtractorTool(BaseTool):
    """
    Tag and keyword extraction tool for OSINT content.
    
    Identifies relevant tags from predefined categories:
    - Threat types (ransomware, malware, etc.)
    - Threat actors (APT groups, etc.)
    - Industry sectors
    - Attack vectors
    - Geographic regions
    """
    
    name: str = "tag_extractor"
    description: str = """Extract relevant OSINT tags from text.
    Identifies: threat types, threat actors, sectors, attack vectors, regions.
    Returns categorized list of tags found in the text."""
    args_schema: Type[BaseModel] = TextAnalysisInput
    
    def _run(
        self,
        text: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Extract tags from text."""
        text_lower = text.lower()
        found_tags: Dict[str, List[str]] = {}
        
        for category, keywords in TAG_KEYWORDS.items():
            matches = []
            for keyword in keywords:
                if keyword in text_lower:
                    matches.append(keyword)
            if matches:
                found_tags[category] = matches
        
        # Also extract capitalized words that might be names/identifiers
        words = re.findall(r'\b[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*\b', text)
        potential_names = [w for w in words if len(w) > 3 and w.lower() not in text_lower]
        
        # Count word frequency for additional keywords
        word_freq = Counter(re.findall(r'\b[a-z]{4,}\b', text_lower))
        common_words = {'that', 'with', 'have', 'this', 'from', 'they', 'will', 'been', 'more'}
        top_keywords = [
            word for word, count in word_freq.most_common(10) 
            if word not in common_words
        ]
        
        return json.dumps({
            "categorized_tags": found_tags,
            "potential_names": potential_names[:10],
            "top_keywords": top_keywords,
            "total_tags": sum(len(v) for v in found_tags.values())
        })
    
    async def _arun(
        self,
        text: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Async version of tag extraction."""
        return self._run(text, run_manager)
