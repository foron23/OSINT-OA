# Changelog

All notable changes to OSINT Agentic Operations will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2025-12-23

### 🏹 Attack Surface Mapping & Infrastructure Intelligence

New AmassAgent integration for comprehensive attack surface mapping and subdomain enumeration.

### Added

#### AmassAgent Integration
- **OWASP Amass integration** for attack surface mapping
  - `AmassAgent` class with subdomain enumeration and organization domain discovery
  - `amass_subdomain_enum` tool for comprehensive subdomain discovery
  - `amass_intel_discovery` tool for organization-based domain enumeration
  - Support for domain, subdomain, attack_surface, infrastructure, reconnaissance, asset_discovery, and organization queries

#### Frontend Integration
- **AmassAgent selection** in both investigation forms
  - Added to "Infrastructure" category in new investigation form
  - Added to "Identity & Infra" category in continue investigation modal
  - Proper labeling: "Amass (Attack Surface)" and "Amass"

#### Testing & Validation
- **Comprehensive test suite** for AmassAgent (`tests/test_amass.py`)
  - 28 test cases covering imports, instantiation, capabilities, and error handling
  - Tool functionality tests for AmassEnumTool and AmassIntelTool
  - Agent registry integration tests
  - Mock-based testing for external tool dependencies

### Technical Details

#### New Agent Implementation (agents/osint/amass.py)
```python
class AmassAgent(BaseOSINTAgent):
    def _define_capabilities(self) -> Dict[str, Any]:
        return {
            "name": "AmassAgent",
            "description": "Attack surface mapping and subdomain enumeration using OWASP Amass",
            "supported_queries": [
                "domain", "subdomain", "attack_surface", "infrastructure",
                "reconnaissance", "asset_discovery", "organization"
            ],
            "max_results": 100,
            "rate_limit_per_minute": 60,
            "requires_api_key": False
        }
```

#### New Tools (tools/amass.py)
- `AmassEnumTool` - Subdomain enumeration via `amass enum`
- `AmassIntelTool` - Organization domain discovery via `amass intel`

## [1.4.0] - 2025-12-22

### 🛡️ Investigation Robustness & Advanced Features

Major update adding robust error handling, agent selection UI, and investigation continuation.

### Added

#### Robust Investigation System
- **Partial completion support** - Investigations now return partial results when errors occur
  - New `InvestigationProgress` class tracks individual agent results
  - `AgentResult` dataclass captures success/failure with timing and IOC count
  - Failed agents don't crash entire investigation
  - Partial reports generated from successful agent results
  
- **Investigation status tracking**
  - New status values: `completed`, `partial`, `failed`
  - Frontend shows appropriate status badges
  - API returns detailed progress information

#### Agent Selection UI
- **Manual agent selection** in new investigation form
  - Toggle between "Auto" mode (recommended) and manual selection
  - Agents grouped by category: Search, Analysis, Identity, Infrastructure
  - "Select All" / "Deselect All" buttons
  
- **Agent validation** in API
  - `/api/collect` now accepts `agents` parameter
  - Invalid agent names return helpful error message

#### Investigation Continuation
- **Continue Investigation feature**
  - New `/api/runs/{id}/continue` endpoint
  - Resume investigations with new instructions
  - Select specific agents for continuation
  - Focus on specific IOCs from previous investigation
  
- **Continue modal in UI**
  - Shows previous query context
  - Depth selection (quick/standard/deep)
  - Agent selection for continuation
  - Previous IOCs available for selection

#### Tests
- `tests/test_control_features.py` - Comprehensive tests for new features
  - InvestigationProgress tracking tests
  - AgentResult dataclass tests
  - Thread-local progress storage tests
  - ControlAgent feature tests
  - Agent selection validation tests
  - Partial report generation tests

### Changed

#### Control Agent
- `investigate()` method now accepts `continue_from` parameter
- Enhanced query includes continuation context when provided
- Returns `progress` dictionary with agent success/failure counts

#### API Routes
- `/api/collect` enhanced with `agents` parameter support
- Response includes `status`, `partial`, and `progress` fields
- Run status updated based on investigation result

#### Frontend
- `startCollection()` handles partial completion messages
- `viewRun()` shows "Continue Investigation" button
- New styles for agent selection and continue modal

### Technical Details

#### New Classes (agents/control.py)
```python
@dataclass
class AgentResult:
    agent_name: str
    success: bool
    result: str = ""
    error: str = ""
    duration_seconds: float = 0.0
    iocs_extracted: int = 0

@dataclass  
class InvestigationProgress:
    run_id: Optional[int]
    topic: str
    depth: str
    started_at: Optional[datetime]
    agent_results: List[AgentResult]
    # ... tracking methods
```

#### New API Endpoint
```
POST /api/runs/{id}/continue

Body:
  new_instructions: string (optional)
  agents: string[] (optional)
  selected_iocs: string[] (optional)
  depth: "quick" | "standard" | "deep" (default: "standard")
  publish_telegram: boolean (default: true)

Response:
  run_id: number (new run)
  continued_from: number (original run)
  status: "completed" | "partial" | "failed"
  ...
```

---

## [1.3.0] - 2025-12-22

### 🔧 Telegram Migration & Agent Registration Fixes

Major update replacing MCP with Telethon and fixing agent registration issues.

### Changed

#### Telegram Integration
- **Migrated from telegram-mcp to Telethon** (Python native library)
  - No external Go binary dependency
  - Better error handling and reconnection logic
  - Full async support
  - Rich HTML formatting for messages
  
- **Updated Docker configuration**
  - Removed telegram-mcp binary from Dockerfiles
  - Session directory changed to `.telegram-session` (hidden folder)
  - Fixed permissions (UID 999 for container user)

#### Agent System
- **Increased recursion limit** from 25 to 50 in `agents/base.py`
  - Prevents "GraphRecursionError" on complex investigations
  - Applied to all LangChain agents via config parameter
  
- **Simplified ControlAgent prompt**
  - Reduced references to `get_shared_evidence_summary`
  - Prevents infinite loop when evidence context unavailable
  - Cleaner workflow instructions

### Added

#### New OSINT Agents
- **HoleheAgent** (`agents/osint/holehe.py`): Email OSINT specialist
  - Checks email registration across 100+ platforms
  - Digital footprint analysis
  
- **PhoneInfogaAgent** (`agents/osint/phoneinfoga.py`): Phone number OSINT
  - Carrier and country identification
  - Line type detection (mobile/landline/VoIP)
  - Social media footprint scanning

#### Telegram API Endpoints
- `GET /api/telegram/status` - Check Telegram connectivity
- `POST /api/telegram/test` - Send test message

#### Telegram Tests
- `tests/test_telegram.py` - 14 tests for Telethon integration
  - Import tests
  - Configuration tests
  - Session directory tests
  - Connectivity tests (skipped when not authenticated)

#### Documentation
- `docs/TELEGRAM_SETUP.md` - Updated setup guide for Telethon

### Fixed

- **Agent registry** - Fixed import error in `api/routes.py`
  - Changed from non-existent `agents.osint_base` to `agents.registry`
  
- **Agent count** - Now 12 agents registered:
  1. TavilySearchAgent
  2. DuckDuckGoSearchAgent
  3. GoogleDorkingAgent
  4. WebScraperAgent
  5. ThreatIntelAgent
  6. IOCAnalysisAgent
  7. HybridOsintAgent
  8. ReportGeneratorAgent
  9. MaigretAgent
  10. BbotAgent
  11. HoleheAgent ✨ NEW
  12. PhoneInfogaAgent ✨ NEW

### Migration Notes

1. **Telegram Session**: Old `session.json` from MCP is incompatible
   ```bash
   docker-compose exec osint-oa python scripts/setup_telegram.py
   ```

2. **Session Directory**: Changed from `telegram-session` to `.telegram-session`
   ```bash
   sudo chown -R 999:999 .telegram-session/
   ```

---

## [1.2.0] - 2025-12-16

### 🔧 OSINT Tools Enhancement & New Integrations

Major update focused on expanding OSINT capabilities with new tools and improving existing ones.

### Added

#### New OSINT Tools (No API Keys Required)
- **HoleheEmailTool** (`tools/holehe.py`): Email registration checker across 100+ platforms
  - Checks if email is registered without alerting the target
  - Uses password recovery endpoints for detection
  - Non-intrusive, stealth operation
  
- **AmassEnumTool** (`tools/amass.py`): OWASP Amass subdomain enumeration
  - Passive and active enumeration modes
  - Uses 20+ data sources (Certificate Transparency, DNS, etc.)
  - Industry-standard attack surface mapping
  
- **AmassIntelTool** (`tools/amass.py`): Organization domain discovery
  - Discovers root domains from organization names
  - Useful for initial reconnaissance
  
- **PhoneInfogaScanTool** (`tools/phoneinfoga.py`): Phone number OSINT
  - Country, carrier, and line type detection
  - Number validation and normalization
  - Social media footprint scanning

#### Unified Test Suite
- `tests/test_osint_tools.py`: **63 tests** covering all OSINT tools
  - Maigret: instantiation, availability, parsing, mock/real execution, validation
  - BBOT: instantiation, availability, parsing, mock/real execution, validation
  - Holehe: instantiation, schema, availability, parsing, integration
  - Amass: instantiation, schema, availability, mock execution, integration
  - PhoneInfoga: instantiation, schema, availability, parsing, integration
  - Module integration: exports, getters, categories

#### Docker Improvements
- Added `git`, `dnsutils`, `whois` to Dockerfiles (required by BBOT)
- Pre-compiled Amass v4.2.0 binary included
- Pre-compiled PhoneInfoga v2.11.0 binary included
- Updated `requirements.txt` with `holehe>=1.61`

#### Telegram Message Formatting
- Rich message formatting with emojis and visual hierarchy
- Severity indicators (🟢🟡🔴) based on exposure level
- Smart truncation at paragraph/sentence boundaries
- New `send_alert()` method for security alerts
- New `send_summary()` method for multi-finding summaries
- Section headers with context-aware emojis

### Changed

#### BBOT Tool Fixes
- Fixed CLI syntax from `-m modules -f flags` to `-p preset -rf require_flags`
- Corrected presets: `subdomain-enum`, `web-basic`, `email-enum`
- Fixed NDJSON parsing for proper output handling
- Added partial results recovery on timeout

#### Maigret Tool Fixes  
- Fixed output syntax from `--json file` to `-J ndjson -fo folder`
- Corrected status parsing from nested `entry["status"]["status"]`
- Fixed output file discovery pattern `*_ndjson.json`

#### Agent Prompts Updated
- `agents/osint/bbot.py`: Updated with correct tool parameters and presets
- `agents/osint/maigret.py`: Updated with correct CLI syntax and methodology

#### Tools Module Reorganization
- Added `get_holehe_tools()`, `get_amass_tools()`, `get_phoneinfoga_tools()` functions
- Updated `get_identity_tools()` to include Holehe and PhoneInfoga
- Added `get_domain_tools()` combining BBOT and Amass
- Updated `get_all_tools()` with new tools

### Documentation
- Updated `docs/LANGCHAIN_ARCHITECTURE.md` with new tools table
- Updated `docs/DOCKER_DEPLOYMENT.md` with OSINT tools section
- Updated `docs/DESARROLLO.md` with v1.3 changes
- Updated `docs/OSINT_TOOLS_SUGGESTIONS.md` marking implemented tools
- Added ethical use disclaimer to README

### Fixed
- BBOT subprocess timeout handling with partial result recovery
- Maigret output file discovery with glob patterns
- Docker missing dependencies for OSINT tools

---

## [1.1.0] - 2024-12-15

### 🛠️ OSINT Tools Integration

### Added
- **Maigret Integration** (`tools/maigret.py`): Username OSINT across 500+ platforms
- **BBOT Integration** (`tools/bbot.py`): Attack surface enumeration
- Modern OSINT tools replacing deprecated OSRFramework

---

## [1.0.0] - 2024-12-15

### 🎉 Initial Release - OSINT Agentic Operations

Complete rebranding and enhancement from "OSINT News Aggregator" to "OSINT Agentic Operations" - a collaborative multi-agent intelligence platform.

### Added

#### Multi-Agent Collaboration System
- **ControlAgent**: Orchestrates investigations across multiple specialized agents
- **10 specialized agents**: Each with unique capabilities for comprehensive OSINT
  - TavilySearchAgent: AI-optimized web search
  - DuckDuckGoSearchAgent: Privacy-focused search
  - GoogleDorkingAgent: Advanced search techniques
  - WebScraperAgent: Deep content extraction
  - ThreatIntelAgent: Threat intelligence with MITRE ATT&CK mapping
  - IOCAnalysisAgent: Indicator of Compromise extraction
  - HybridOsintAgent: Multi-tool comprehensive analysis
  - MaigretAgent: Username OSINT across 500+ platforms
  - BbotAgent: Domain reconnaissance and attack surface enumeration
  - ReportGeneratorAgent: Report formatting and synthesis

#### Evidence Collection System
- Automatic IOC extraction from all agent outputs
- Structured evidence format with JSON schema
- IOC types supported:
  - IP addresses (IPv4/IPv6)
  - Domain names
  - URLs
  - File hashes (MD5, SHA1, SHA256)
  - Email addresses
  - CVE identifiers
  - Cryptocurrency addresses
- Entity extraction (threat actors, malware, organizations)
- MITRE ATT&CK technique mapping
- Confidence scoring (0.0-1.0)

#### Investigation Tracing
- `TracingContext`: Context manager for hierarchical trace recording
- Full execution traceability:
  - Agent actions and decisions
  - Tool invocations with parameters
  - LLM reasoning steps
  - Evidence found at each step
- Trace summary API endpoints
- Evidence aggregation per investigation

#### Enhanced System Prompts
- Comprehensive prompts for all agents emphasizing:
  - Collaborative investigation mindset
  - Mandatory IOC extraction
  - Structured JSON output format
  - MITRE ATT&CK mapping where applicable
  - Confidence scoring requirements
  - Source attribution

#### Frontend Updates
- **Hacker Theme**: Black/red color scheme with glow effects
- Markdown rendering for investigation reports (via marked.js)
- Trace visualization in investigation details
- Responsive design with terminal-style aesthetics

#### Telegram Integration
- Listener for `/osint` commands
- Automatic report publishing to configured dialogs
- Run ID tracking for investigations initiated via Telegram
- Support for quick/standard/deep investigation depths

#### API Enhancements
- `/api/runs/<id>/traces` - Get all traces for an investigation
- `/api/runs/<id>/traces/summary` - Get evidence summary statistics
- `/api/runs/<id>/traces/<trace_id>` - Get detailed trace information
- `/api/runs/<id>/traces/<trace_id>/evidence` - Get only evidence from a trace
- `/api/traces/recent` - Get recent traces across all runs

### Changed

#### Architecture Rebranding
- Updated all module headers and documentation
- Shifted focus from news aggregation to comprehensive OSINT investigations

#### Agent System Improvements
- `LangChainAgent.run()` now accepts `run_id` for tracing
- Added `_extract_evidence_from_result()` method to base agent
- Added `_calculate_confidence()` method for automatic scoring
- Enhanced `_get_system_prompt()` with evidence collection requirements

#### Database Schema
- Added `traces` table for execution tracing
- Added `evidence_found_json` column for structured evidence storage
- Added `confidence_score` column for reliability assessment

### Technical Details

#### Dependencies
- LangChain + LangGraph for agent orchestration
- OpenAI GPT-4o-mini for LLM reasoning
- Tavily API for AI-optimized search
- marked.js for frontend Markdown rendering

#### Test Suite
- 108 tests covering:
  - Agent instantiation and capabilities
  - Tool functionality
  - Integration workflows
  - Database operations
  - API endpoints

### Documentation
- Comprehensive README with architecture diagrams
- Agent development guide
- Tool creation instructions
- API reference

---

## [0.9.0] - 2024-12-14 (Pre-release)

### Added
- Initial Telegram listener with command processing
- Investigation flow matching web API
- Report publishing to Telegram dialogs

### Fixed
- Telegram MCP client initialization
- Async/await handling in listener
- Run ID tracking for Telegram investigations

---

## [0.8.0] - 2024-12-13 (Pre-release)

### Added
- Basic agent registry with capability discovery
- Control agent for investigation orchestration
- Consolidator agent for report publishing

### Changed
- Migrated from legacy agents to LangChain ReAct pattern

---

## Future Roadmap

### Planned for v1.1.0
- [ ] Real-time IOC reputation checking
- [ ] Integration with VirusTotal API
- [ ] STIX/TAXII export format
- [ ] Scheduled automated investigations

### Planned for v1.2.0
- [ ] Multi-user support with authentication
- [ ] Investigation sharing and collaboration
- [ ] Custom agent creation via UI
- [ ] Webhook notifications

### Planned for v2.0.0
- [ ] Distributed agent execution
- [ ] GPU-accelerated analysis
- [ ] Knowledge graph visualization
- [ ] Machine learning anomaly detection
