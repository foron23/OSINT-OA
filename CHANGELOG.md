# Changelog

All notable changes to OSINT Agentic Operations will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- Renamed from "OSINT News Aggregator" to "OSINT Agentic Operations"
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
