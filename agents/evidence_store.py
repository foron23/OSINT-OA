# =============================================================================
# Evidence Store - Shared Evidence Management for Multi-Agent Investigations
# =============================================================================
"""
Centralized evidence store for sharing IOCs and findings between agents.

This module solves the problem of agents working in isolation by providing:
- A shared in-memory store for evidence (IOCs, entities, findings)
- Automatic evidence deduplication
- Evidence enrichment when multiple agents find the same IOC
- Cross-agent correlation capabilities
- Feedback mechanism to re-feed relevant IOCs to appropriate agents

Architecture:
    ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
    │  SearchAgent    │──────►│  EvidenceStore  │◄──────│  MaigretAgent   │
    │                 │◄──────│  (Shared State) │──────►│                 │
    └─────────────────┘       └─────────────────┘       └─────────────────┘
                                      │
                              ┌───────┴───────┐
                              │  IOC Routing  │
                              │  & Enrichment │
                              └───────────────┘

Usage:
    from agents.evidence_store import EvidenceStore, Evidence, IOC
    
    # Get store for a specific investigation
    store = EvidenceStore.get_or_create(run_id=123)
    
    # Add evidence from an agent
    store.add_ioc(IOC(type="domain", value="evil.com", source_agent="SearchAgent"))
    
    # Get IOCs relevant to another agent
    usernames = store.get_iocs_for_agent("MaigretAgent")
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Callable
from enum import Enum
from threading import Lock
import json

logger = logging.getLogger(__name__)


# =============================================================================
# IOC Types and Evidence Models
# =============================================================================

class IOCType(str, Enum):
    """Types of Indicators of Compromise."""
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    EMAIL = "email"
    HASH_MD5 = "hash_md5"
    HASH_SHA1 = "hash_sha1"
    HASH_SHA256 = "hash_sha256"
    CVE = "cve"
    USERNAME = "username"
    HANDLE = "handle"
    PHONE = "phone"
    CRYPTOCURRENCY = "crypto"
    MITRE_TECHNIQUE = "mitre"
    MALWARE = "malware"
    THREAT_ACTOR = "threat_actor"
    ORGANIZATION = "organization"
    FILE_PATH = "file_path"
    REGISTRY_KEY = "registry_key"


class AgentType(str, Enum):
    """Types of OSINT agents with their specializations."""
    SEARCH = "search"           # Web search agents
    DOMAIN = "domain"           # Domain/subdomain reconnaissance
    USERNAME = "username"       # Username OSINT
    THREAT_INTEL = "threat"     # Threat intelligence
    IOC_ANALYSIS = "ioc"        # IOC enrichment
    PHONE = "phone"             # Phone number OSINT
    EMAIL = "email"             # Email verification
    HYBRID = "hybrid"           # Multi-purpose


# Agent to IOC type mapping - what IOCs are useful for each agent type
AGENT_IOC_RELEVANCE: Dict[AgentType, List[IOCType]] = {
    AgentType.SEARCH: [IOCType.DOMAIN, IOCType.ORGANIZATION, IOCType.THREAT_ACTOR, IOCType.MALWARE],
    AgentType.DOMAIN: [IOCType.DOMAIN, IOCType.IP, IOCType.URL],
    AgentType.USERNAME: [IOCType.USERNAME, IOCType.HANDLE, IOCType.EMAIL],
    AgentType.THREAT_INTEL: [IOCType.CVE, IOCType.MITRE_TECHNIQUE, IOCType.THREAT_ACTOR, IOCType.MALWARE],
    AgentType.IOC_ANALYSIS: [IOCType.IP, IOCType.DOMAIN, IOCType.HASH_MD5, IOCType.HASH_SHA1, IOCType.HASH_SHA256],
    AgentType.PHONE: [IOCType.PHONE],
    AgentType.EMAIL: [IOCType.EMAIL],
    AgentType.HYBRID: list(IOCType),  # Hybrid gets everything
}

# Agent name to type mapping
AGENT_TYPE_MAP: Dict[str, AgentType] = {
    "TavilySearchAgent": AgentType.SEARCH,
    "DuckDuckGoSearchAgent": AgentType.SEARCH,
    "GoogleDorkingAgent": AgentType.SEARCH,
    "BbotAgent": AgentType.DOMAIN,
    "MaigretAgent": AgentType.USERNAME,
    "ThreatIntelAgent": AgentType.THREAT_INTEL,
    "IOCAnalysisAgent": AgentType.IOC_ANALYSIS,
    "PhoneInfogaAgent": AgentType.PHONE,
    "HolehAgent": AgentType.EMAIL,
    "HybridOsintAgent": AgentType.HYBRID,
    "ControlAgent": AgentType.HYBRID,
}


@dataclass
class IOC:
    """An Indicator of Compromise with enrichment data."""
    type: IOCType
    value: str
    source_agent: str
    context: str = ""
    confidence: float = 0.8
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    sources: List[str] = field(default_factory=list)
    enrichments: Dict[str, Any] = field(default_factory=dict)
    
    # Track which agents have seen/used this IOC
    seen_by_agents: Set[str] = field(default_factory=set)
    fed_to_agents: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        # Normalize value based on type
        self.value = self._normalize_value()
        self.seen_by_agents.add(self.source_agent)
    
    def _normalize_value(self) -> str:
        """Normalize IOC value for deduplication."""
        value = self.value.strip()
        
        if self.type in [IOCType.DOMAIN, IOCType.EMAIL]:
            value = value.lower()
        elif self.type == IOCType.URL:
            value = value.rstrip('/')
        elif self.type in [IOCType.HASH_MD5, IOCType.HASH_SHA1, IOCType.HASH_SHA256]:
            value = value.lower()
        elif self.type == IOCType.USERNAME:
            value = value.lstrip('@').lower()
        
        return value
    
    @property
    def unique_key(self) -> str:
        """Generate unique key for deduplication."""
        return f"{self.type.value}:{self.value}"
    
    def merge_with(self, other: 'IOC') -> 'IOC':
        """Merge enrichments from another IOC instance."""
        if self.unique_key != other.unique_key:
            raise ValueError("Cannot merge IOCs with different keys")
        
        # Update confidence (take max)
        self.confidence = max(self.confidence, other.confidence)
        
        # Merge sources
        for src in other.sources:
            if src not in self.sources:
                self.sources.append(src)
        
        # Merge enrichments
        self.enrichments.update(other.enrichments)
        
        # Merge context if different
        if other.context and other.context not in self.context:
            self.context = f"{self.context}; {other.context}" if self.context else other.context
        
        # Track agents
        self.seen_by_agents.update(other.seen_by_agents)
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type.value,
            "value": self.value,
            "source_agent": self.source_agent,
            "context": self.context,
            "confidence": self.confidence,
            "first_seen": self.first_seen,
            "sources": self.sources,
            "enrichments": self.enrichments,
            "seen_by_agents": list(self.seen_by_agents),
            "fed_to_agents": list(self.fed_to_agents),
        }


@dataclass
class Finding:
    """A finding or insight discovered during investigation."""
    title: str
    description: str
    source_agent: str
    source_url: Optional[str] = None
    confidence: float = 0.8
    relevance: float = 0.8
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    related_iocs: List[str] = field(default_factory=list)  # IOC unique keys
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "source_agent": self.source_agent,
            "source_url": self.source_url,
            "confidence": self.confidence,
            "relevance": self.relevance,
            "timestamp": self.timestamp,
            "related_iocs": self.related_iocs,
            "tags": self.tags,
        }


@dataclass 
class EvidenceStats:
    """Statistics about collected evidence."""
    total_iocs: int = 0
    total_findings: int = 0
    iocs_by_type: Dict[str, int] = field(default_factory=dict)
    iocs_by_agent: Dict[str, int] = field(default_factory=dict)
    cross_referenced_iocs: int = 0
    enriched_iocs: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_iocs": self.total_iocs,
            "total_findings": self.total_findings,
            "iocs_by_type": self.iocs_by_type,
            "iocs_by_agent": self.iocs_by_agent,
            "cross_referenced_iocs": self.cross_referenced_iocs,
            "enriched_iocs": self.enriched_iocs,
        }


# =============================================================================
# Evidence Store
# =============================================================================

class EvidenceStore:
    """
    Centralized store for sharing evidence between agents.
    
    Thread-safe singleton per run_id.
    Provides:
    - IOC storage with automatic deduplication
    - Findings aggregation
    - Agent-specific IOC filtering
    - Enrichment tracking
    - Statistics
    """
    
    # Class-level storage for stores by run_id
    _stores: Dict[int, 'EvidenceStore'] = {}
    _stores_lock = Lock()
    
    @classmethod
    def get_or_create(cls, run_id: int) -> 'EvidenceStore':
        """Get existing store or create new one for a run."""
        with cls._stores_lock:
            if run_id not in cls._stores:
                cls._stores[run_id] = cls(run_id)
                logger.info(f"Created new EvidenceStore for run #{run_id}")
            return cls._stores[run_id]
    
    @classmethod
    def get(cls, run_id: int) -> Optional['EvidenceStore']:
        """Get existing store for a run, or None if not exists."""
        with cls._stores_lock:
            return cls._stores.get(run_id)
    
    @classmethod
    def cleanup(cls, run_id: int):
        """Remove store for a completed run."""
        with cls._stores_lock:
            if run_id in cls._stores:
                del cls._stores[run_id]
                logger.info(f"Cleaned up EvidenceStore for run #{run_id}")
    
    def __init__(self, run_id: int):
        """Initialize the evidence store for a specific run."""
        self.run_id = run_id
        self.created_at = datetime.now().isoformat()
        
        # IOC storage: unique_key -> IOC
        self._iocs: Dict[str, IOC] = {}
        self._iocs_lock = Lock()
        
        # Findings storage
        self._findings: List[Finding] = []
        self._findings_lock = Lock()
        
        # Callbacks for IOC routing
        self._ioc_callbacks: List[Callable[[IOC], None]] = []
        
        # Statistics
        self._stats = EvidenceStats()
        
        self.logger = logging.getLogger(f"EvidenceStore-{run_id}")
    
    # =========================================================================
    # IOC Management
    # =========================================================================
    
    def add_ioc(self, ioc: IOC) -> IOC:
        """
        Add an IOC to the store.
        
        Automatically deduplicates and merges enrichments.
        
        Args:
            ioc: The IOC to add
            
        Returns:
            The IOC (merged if duplicate)
        """
        with self._iocs_lock:
            key = ioc.unique_key
            
            if key in self._iocs:
                # Merge with existing
                existing = self._iocs[key]
                existing.merge_with(ioc)
                self.logger.debug(f"Merged IOC: {key} (now {len(existing.seen_by_agents)} agents)")
                self._stats.cross_referenced_iocs += 1
                return existing
            else:
                # New IOC
                self._iocs[key] = ioc
                self._stats.total_iocs += 1
                
                # Update stats
                ioc_type = ioc.type.value
                self._stats.iocs_by_type[ioc_type] = self._stats.iocs_by_type.get(ioc_type, 0) + 1
                self._stats.iocs_by_agent[ioc.source_agent] = self._stats.iocs_by_agent.get(ioc.source_agent, 0) + 1
                
                self.logger.info(f"New IOC from {ioc.source_agent}: {key}")
                
                # Trigger callbacks for new IOC
                for callback in self._ioc_callbacks:
                    try:
                        callback(ioc)
                    except Exception as e:
                        self.logger.error(f"IOC callback error: {e}")
                
                return ioc
    
    def add_iocs_from_text(self, text: str, source_agent: str, context: str = "") -> List[IOC]:
        """
        Extract and add IOCs from raw text.
        
        Uses regex patterns to find common IOC types.
        
        Args:
            text: Text to extract IOCs from
            source_agent: Name of the agent that found this text
            context: Additional context about the source
            
        Returns:
            List of added IOCs
        """
        added = []
        
        # IOC patterns
        patterns = {
            IOCType.IP: r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
            IOCType.DOMAIN: r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:com|net|org|io|gov|edu|info|biz|co|uk|de|ru|cn|jp|fr|it|es|nl|au|ca|br|in|kr|mx|se|ch|at|be|pl|cz|hu|ro|bg|sk|lt|lv|ee|fi|no|dk|ie|pt|gr|il|tr|za|sg|hk|tw|my|id|ph|th|vn|nz|ae|sa|eg|ng|ke|online|xyz|tech|site|club|top|vip|work|live|pro|app|dev|cloud|ai)\b',
            IOCType.URL: r'https?://[^\s<>"\'}\]\)]+',
            IOCType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            IOCType.HASH_MD5: r'\b[a-fA-F0-9]{32}\b',
            IOCType.HASH_SHA1: r'\b[a-fA-F0-9]{40}\b',
            IOCType.HASH_SHA256: r'\b[a-fA-F0-9]{64}\b',
            IOCType.CVE: r'\bCVE-\d{4}-\d{4,7}\b',
            IOCType.USERNAME: r'@[a-zA-Z_][a-zA-Z0-9_]{2,30}\b',
            IOCType.MITRE_TECHNIQUE: r'\bT\d{4}(?:\.\d{3})?\b',
            IOCType.PHONE: r'\+?[1-9]\d{1,2}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
        }
        
        # False positives to skip
        false_positives = {
            'example.com', 'test.com', 'domain.com', 'localhost',
            'google.com', 'github.com', 'twitter.com', 'facebook.com',
            'youtube.com', 'instagram.com', 'linkedin.com', 'microsoft.com',
            'apple.com', 'amazon.com', 'wikipedia.org',
        }
        
        seen = set()
        
        for ioc_type, pattern in patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = match.group().strip()
                
                # Skip false positives
                if value.lower() in false_positives:
                    continue
                
                # Skip duplicates in same extraction
                key = f"{ioc_type.value}:{value.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                
                ioc = IOC(
                    type=ioc_type,
                    value=value,
                    source_agent=source_agent,
                    context=context,
                    confidence=0.75,
                )
                added.append(self.add_ioc(ioc))
        
        if added:
            self.logger.info(f"Extracted {len(added)} IOCs from text by {source_agent}")
        
        return added
    
    def get_ioc(self, unique_key: str) -> Optional[IOC]:
        """Get an IOC by its unique key."""
        with self._iocs_lock:
            return self._iocs.get(unique_key)
    
    def get_all_iocs(self) -> List[IOC]:
        """Get all IOCs in the store."""
        with self._iocs_lock:
            return list(self._iocs.values())
    
    def get_iocs_by_type(self, ioc_type: IOCType) -> List[IOC]:
        """Get all IOCs of a specific type."""
        with self._iocs_lock:
            return [ioc for ioc in self._iocs.values() if ioc.type == ioc_type]
    
    def get_iocs_for_agent(
        self,
        agent_name: str,
        exclude_already_fed: bool = True,
        max_count: int = 20
    ) -> List[IOC]:
        """
        Get IOCs relevant to a specific agent.
        
        Uses AGENT_IOC_RELEVANCE to determine which IOC types
        are useful for each agent type.
        
        Args:
            agent_name: Name of the agent requesting IOCs
            exclude_already_fed: Skip IOCs already fed to this agent
            max_count: Maximum number of IOCs to return
            
        Returns:
            List of relevant IOCs sorted by confidence
        """
        agent_type = AGENT_TYPE_MAP.get(agent_name, AgentType.HYBRID)
        relevant_types = AGENT_IOC_RELEVANCE.get(agent_type, list(IOCType))
        
        with self._iocs_lock:
            relevant = []
            for ioc in self._iocs.values():
                # Skip IOCs not relevant to this agent type
                if ioc.type not in relevant_types:
                    continue
                
                # Skip if already fed to this agent
                if exclude_already_fed and agent_name in ioc.fed_to_agents:
                    continue
                
                # Skip if agent discovered this IOC themselves
                if ioc.source_agent == agent_name:
                    continue
                
                relevant.append(ioc)
            
            # Sort by confidence descending
            relevant.sort(key=lambda x: x.confidence, reverse=True)
            
            # Mark as fed to this agent
            result = relevant[:max_count]
            for ioc in result:
                ioc.fed_to_agents.add(agent_name)
            
            return result
    
    def get_high_value_iocs(self, min_confidence: float = 0.8, min_sources: int = 2) -> List[IOC]:
        """Get high-value IOCs that have been cross-referenced."""
        with self._iocs_lock:
            return [
                ioc for ioc in self._iocs.values()
                if ioc.confidence >= min_confidence or len(ioc.seen_by_agents) >= min_sources
            ]
    
    def enrich_ioc(self, unique_key: str, enrichments: Dict[str, Any]) -> Optional[IOC]:
        """
        Add enrichment data to an existing IOC.
        
        Args:
            unique_key: The IOC's unique key
            enrichments: Dictionary of enrichment data
            
        Returns:
            Updated IOC or None if not found
        """
        with self._iocs_lock:
            if unique_key in self._iocs:
                ioc = self._iocs[unique_key]
                ioc.enrichments.update(enrichments)
                self._stats.enriched_iocs += 1
                self.logger.debug(f"Enriched IOC: {unique_key}")
                return ioc
            return None
    
    # =========================================================================
    # Finding Management
    # =========================================================================
    
    def add_finding(self, finding: Finding) -> Finding:
        """Add a finding to the store."""
        with self._findings_lock:
            self._findings.append(finding)
            self._stats.total_findings += 1
            self.logger.info(f"New finding from {finding.source_agent}: {finding.title[:50]}...")
            return finding
    
    def get_all_findings(self) -> List[Finding]:
        """Get all findings."""
        with self._findings_lock:
            return list(self._findings)
    
    def get_findings_by_agent(self, agent_name: str) -> List[Finding]:
        """Get findings from a specific agent."""
        with self._findings_lock:
            return [f for f in self._findings if f.source_agent == agent_name]
    
    # =========================================================================
    # Callbacks and Routing
    # =========================================================================
    
    def register_ioc_callback(self, callback: Callable[[IOC], None]):
        """
        Register a callback to be called when new IOCs are added.
        
        Useful for real-time IOC routing to other agents.
        """
        self._ioc_callbacks.append(callback)
    
    def create_feedback_prompt(self, agent_name: str) -> Optional[str]:
        """
        Create a feedback prompt for an agent with relevant IOCs.
        
        This is the core of the evidence feedback mechanism - it generates
        a prompt that includes IOCs discovered by OTHER agents that might
        be useful for this agent's investigation.
        
        Args:
            agent_name: Name of the agent to create prompt for
            
        Returns:
            Prompt string with relevant IOCs, or None if no relevant IOCs
        """
        iocs = self.get_iocs_for_agent(agent_name, exclude_already_fed=True)
        
        if not iocs:
            return None
        
        prompt_lines = [
            "=== ADDITIONAL INTELLIGENCE FROM OTHER AGENTS ===",
            "",
            "The following indicators were discovered by other agents during this investigation.",
            "Consider using them to deepen your analysis:",
            "",
        ]
        
        # Group IOCs by type
        by_type: Dict[IOCType, List[IOC]] = {}
        for ioc in iocs:
            if ioc.type not in by_type:
                by_type[ioc.type] = []
            by_type[ioc.type].append(ioc)
        
        for ioc_type, type_iocs in by_type.items():
            prompt_lines.append(f"**{ioc_type.value.upper()}s:**")
            for ioc in type_iocs[:5]:  # Max 5 per type
                source_info = f"(from {ioc.source_agent}, conf: {ioc.confidence:.0%})"
                prompt_lines.append(f"  • {ioc.value} {source_info}")
                if ioc.context:
                    prompt_lines.append(f"    Context: {ioc.context[:100]}")
            prompt_lines.append("")
        
        prompt_lines.extend([
            "Use these indicators to:",
            "- Search for additional related information",
            "- Cross-reference with your findings",
            "- Identify connections and patterns",
            "",
            "=== END ADDITIONAL INTELLIGENCE ===",
        ])
        
        return "\n".join(prompt_lines)
    
    # =========================================================================
    # Statistics and Export
    # =========================================================================
    
    def get_stats(self) -> EvidenceStats:
        """Get current statistics."""
        return self._stats
    
    def to_dict(self) -> Dict[str, Any]:
        """Export store contents to dictionary."""
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "iocs": [ioc.to_dict() for ioc in self.get_all_iocs()],
            "findings": [f.to_dict() for f in self.get_all_findings()],
            "stats": self._stats.to_dict(),
        }
    
    def get_investigation_summary(self) -> str:
        """Generate a human-readable summary of collected evidence."""
        stats = self._stats
        iocs = self.get_all_iocs()
        findings = self.get_all_findings()
        
        summary = [
            f"## Evidence Summary (Run #{self.run_id})",
            "",
            f"**Total IOCs:** {stats.total_iocs}",
            f"**Cross-referenced:** {stats.cross_referenced_iocs}",
            f"**Enriched:** {stats.enriched_iocs}",
            f"**Findings:** {stats.total_findings}",
            "",
        ]
        
        if stats.iocs_by_type:
            summary.append("### IOCs by Type:")
            for ioc_type, count in sorted(stats.iocs_by_type.items(), key=lambda x: x[1], reverse=True):
                summary.append(f"  • {ioc_type}: {count}")
            summary.append("")
        
        if stats.iocs_by_agent:
            summary.append("### IOCs by Source Agent:")
            for agent, count in sorted(stats.iocs_by_agent.items(), key=lambda x: x[1], reverse=True):
                summary.append(f"  • {agent}: {count}")
            summary.append("")
        
        # High value IOCs
        high_value = self.get_high_value_iocs()
        if high_value:
            summary.append("### High-Value IOCs (cross-referenced or high confidence):")
            for ioc in high_value[:10]:
                agents = ", ".join(ioc.seen_by_agents)
                summary.append(f"  • [{ioc.type.value}] {ioc.value} (agents: {agents})")
            summary.append("")
        
        return "\n".join(summary)


# =============================================================================
# Helper function for agent integration
# =============================================================================

def get_evidence_context(run_id: int, agent_name: str) -> Dict[str, Any]:
    """
    Get evidence context for an agent.
    
    Returns a dictionary with:
    - feedback_prompt: Prompt with relevant IOCs from other agents
    - relevant_iocs: List of IOC dicts relevant to this agent
    - store: Reference to the EvidenceStore
    """
    store = EvidenceStore.get(run_id)
    
    if not store:
        return {
            "feedback_prompt": None,
            "relevant_iocs": [],
            "store": None,
        }
    
    return {
        "feedback_prompt": store.create_feedback_prompt(agent_name),
        "relevant_iocs": [ioc.to_dict() for ioc in store.get_iocs_for_agent(agent_name)],
        "store": store,
    }
