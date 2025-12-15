# Changelog

All notable changes to OSINT Agentic Operations will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-12-15

### 🐛 Bug Fixes

#### Docker Volume Permissions
- **Fixed database read-only error**: Added `fix_permissions()` function in entrypoint that automatically corrects volume permissions when Docker volumes are mounted
- **Telegram session loading**: Fixed bind mount configuration for `./telegram-session` directory to properly load existing sessions

#### Frontend Improvements
- **Evidence Items section**: Now extracts and displays structured findings from investigation reports
  - Parses markdown reports to extract key findings, links, and IOCs
  - Shows IOCs in a dedicated badge format
  - Displays section context for each finding

### ✨ Enhancements

#### Matrix-Style UI Effects
- Added subtle Matrix-inspired animations to the hacker theme:
  - Scanline effect overlay
  - Flicker animation for CRT monitor feel
  - Pulse glow on interactive elements
  - Fade-in animations for cards and panels
  - Terminal cursor blink on header
- All animations respect `prefers-reduced-motion` accessibility setting

#### Improved Error Handling
- Backend now returns specific error types (`database_readonly`, `database_locked`, etc.)
- Frontend translates technical errors to user-friendly messages
- Better error messages guide users on how to resolve issues

### 🔧 Changes

#### Rebranding
- Renamed from "OSINT News Aggregator" to "OSINT Aggregator" throughout
- Updated page title, headers, and documentation

#### Docker Compose
- Removed obsolete `version` attribute from docker-compose files
- Improved documentation in docker-compose.prod.yml
- Changed telegram-session from Docker volume to bind mount for easier session management

### 📚 Documentation
- Updated CHANGELOG with v1.0.1 changes
- Added Telegram usage guide section

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
