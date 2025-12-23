# =============================================================================
# OSINT OA - bbot Tools
# =============================================================================
"""
bbot integration tools for attack surface enumeration.

bbot is a comprehensive OSINT and attack surface enumeration tool.
It excels at subdomain enumeration, web reconnaissance, and vulnerability discovery.

GitHub: https://github.com/blacklanternsecurity/bbot
Install: pip install bbot

Provides:
- BbotSubdomainTool: Subdomain enumeration
- BbotWebScanTool: Web reconnaissance and content discovery
- BbotEmailTool: Email harvesting
"""

import json
import logging
import asyncio
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Type, List, Any

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun

logger = logging.getLogger(__name__)


# =============================================================================
# Input Schemas
# =============================================================================

class BbotDomainInput(BaseModel):
    """Input for bbot domain scanning."""
    domain: str = Field(description="Target domain to scan (e.g., example.com)")
    modules: Optional[List[str]] = Field(
        default=None, 
        description="Specific modules to run (e.g., subdomains, httpx, wayback)"
    )


class BbotSubdomainInput(BaseModel):
    """Input for subdomain enumeration."""
    domain: str = Field(description="Target domain for subdomain enumeration")
    passive_only: bool = Field(
        default=True, 
        description="Only use passive sources (no active scanning)"
    )


class BbotEmailInput(BaseModel):
    """Input for email harvesting."""
    domain: str = Field(description="Target domain for email discovery")


# =============================================================================
# Helper Functions
# =============================================================================

def _check_bbot_available() -> bool:
    """Check if bbot is installed and available."""
    return shutil.which('bbot') is not None


async def _run_bbot_async(
    target: str,
    preset: Optional[str] = None,
    modules: Optional[List[str]] = None,
    require_flags: Optional[List[str]] = None,
    output_modules: Optional[List[str]] = None,
    timeout_minutes: int = 10
) -> dict:
    """
    Run bbot asynchronously and return results.
    
    Args:
        target: Target domain or IP
        preset: Preset to use (e.g., subdomain-enum, web-basic, spider)
        modules: Additional specific modules to run (e.g., httpx, nuclei)
        require_flags: Filter modules by required flags (e.g., passive)
        output_modules: Output modules (e.g., json)
        timeout_minutes: Maximum runtime in minutes
        
    Returns:
        Dictionary with scan results
    """
    if not _check_bbot_available():
        return {
            "success": False,
            "error": "bbot not installed. Install with: pip install bbot",
            "results": []
        }
    
    # Create temporary directory for output
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "bbot_output"
        scan_name = f"scan_{target.replace('.', '_')}"
        
        cmd = [
            'bbot',
            '-t', target,
            '-o', str(output_dir),
            '-n', scan_name,
            '--silent',
            '-y',  # Yes to all prompts
        ]
        
        # Use preset if specified (recommended approach)
        if preset:
            cmd.extend(['-p', preset])
        
        # Add specific modules if provided
        if modules:
            cmd.extend(['-m'] + modules)
        
        # Filter by required flags (e.g., passive)
        if require_flags:
            cmd.extend(['-rf'] + require_flags)
        
        # Always output JSON format
        cmd.extend(['-om', 'json'])
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_minutes * 60
            )
            
            # Parse output from JSON file
            # BBOT creates output in: output_dir/scan_name/output.json (NDJSON format)
            scan_output_dir = output_dir / scan_name
            json_output = scan_output_dir / "output.json"
            ndjson_output = scan_output_dir / "output.ndjson"
            
            results = []
            
            # Function to parse NDJSON content
            def parse_ndjson(file_path):
                parsed = []
                with open(file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                parsed.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
                return parsed
            
            # BBOT output.json is actually NDJSON format (one JSON per line)
            if json_output.exists():
                results = parse_ndjson(json_output)
            elif ndjson_output.exists():
                results = parse_ndjson(ndjson_output)
            
            # Parse stdout for events if no file output
            if not results:
                output = stdout.decode('utf-8', errors='ignore')
                for line in output.split('\n'):
                    if line.strip():
                        try:
                            results.append(json.loads(line))
                        except json.JSONDecodeError:
                            # Not JSON, might be a status message
                            if any(keyword in line.lower() for keyword in ['found', 'discovered', 'dns_name', 'email']):
                                results.append({"raw": line.strip()})
            
            return {
                "success": True,
                "target": target,
                "preset": preset or "default",
                "modules": modules or [],
                "events_found": len(results),
                "results": results[:100],  # Limit results
                "error": None
            }
            
        except asyncio.TimeoutError:
            # Try to read partial results even on timeout
            partial_results = []
            try:
                if json_output.exists():
                    partial_results = parse_ndjson(json_output)
                elif ndjson_output.exists():
                    partial_results = parse_ndjson(ndjson_output)
            except Exception:
                pass
            
            return {
                "success": len(partial_results) > 0,
                "target": target,
                "error": f"bbot scan timed out after {timeout_minutes} minutes (partial results may be available)",
                "events_found": len(partial_results),
                "results": partial_results[:100]
            }
        except Exception as e:
            return {
                "success": False,
                "target": target,
                "error": str(e),
                "results": []
            }


def _run_bbot_sync(
    target: str,
    preset: Optional[str] = None,
    modules: Optional[List[str]] = None,
    require_flags: Optional[List[str]] = None,
    timeout_minutes: int = 10
) -> dict:
    """Synchronous wrapper for bbot."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        _run_bbot_async(target, preset=preset, modules=modules, require_flags=require_flags, timeout_minutes=timeout_minutes)
    )


# =============================================================================
# Subdomain Enumeration Tool
# =============================================================================

class BbotSubdomainTool(BaseTool):
    """
    Enumerate subdomains of a target domain using bbot.
    
    Uses the subdomain-enum preset with multiple sources:
    - Certificate transparency logs (crt.sh, certspotter)
    - DNS records and zone transfers
    - Wayback Machine archives
    - Public subdomain databases
    - Search engine results
    """
    
    name: str = "bbot_subdomain_enum"
    description: str = """Enumerate subdomains of a target domain using passive OSINT sources.
Uses bbot's subdomain-enum preset which queries certificate transparency logs, DNS records, web archives, and public databases.
Input: domain (e.g., 'example.com'), passive_only (bool, default True)
Returns: List of discovered subdomains with their status.
Example usage: Search for subdomains of a company's main domain."""
    args_schema: Type[BaseModel] = BbotSubdomainInput
    
    def _run(
        self,
        domain: str,
        passive_only: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run subdomain enumeration synchronously."""
        # Use subdomain-enum preset which is the recommended way
        preset = "subdomain-enum"
        require_flags = ["passive"] if passive_only else None
        
        result = _run_bbot_sync(domain, preset=preset, require_flags=require_flags, timeout_minutes=5)
        
        # Extract just subdomains from results
        if result["success"]:
            subdomains = []
            for event in result.get("results", []):
                if isinstance(event, dict):
                    if event.get("type") == "DNS_NAME":
                        subdomains.append(event.get("data", ""))
                    elif "dns_name" in str(event).lower():
                        subdomains.append(str(event.get("data", event.get("raw", ""))))
            
            result["subdomains"] = list(set(subdomains))
            result["subdomain_count"] = len(result["subdomains"])
        
        return json.dumps(result, indent=2, default=str)
    
    async def _arun(
        self,
        domain: str,
        passive_only: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run subdomain enumeration asynchronously."""
        # Use subdomain-enum preset which is the recommended way
        preset = "subdomain-enum"
        require_flags = ["passive"] if passive_only else None
        
        result = await _run_bbot_async(domain, preset=preset, require_flags=require_flags, timeout_minutes=5)
        
        if result["success"]:
            subdomains = []
            for event in result.get("results", []):
                if isinstance(event, dict):
                    if event.get("type") == "DNS_NAME":
                        subdomains.append(event.get("data", ""))
            
            result["subdomains"] = list(set(subdomains))
            result["subdomain_count"] = len(result["subdomains"])
        
        return json.dumps(result, indent=2, default=str)


# =============================================================================
# Web Reconnaissance Tool
# =============================================================================

class BbotWebScanTool(BaseTool):
    """
    Perform web reconnaissance on a target domain using bbot.
    
    Uses the web-basic preset to discover:
    - Web technologies (frameworks, servers, CMS)
    - robots.txt and security.txt files
    - Exposed endpoints and paths
    - HTTP headers and security configurations
    """
    
    name: str = "bbot_web_recon"
    description: str = """Perform web reconnaissance on a target domain or URL.
Uses bbot's web-basic preset to analyze web technologies, security configurations, and exposed endpoints.
Input: domain (e.g., 'www.example.com'), modules (optional list of additional modules)
Returns: Web reconnaissance findings including technologies, URLs, and potential issues.
Example usage: Analyze what technologies a website is using."""
    args_schema: Type[BaseModel] = BbotDomainInput
    
    def _run(
        self,
        domain: str,
        modules: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run web recon synchronously."""
        # Use web-basic preset with optional additional modules
        preset = "web-basic"
        extra_modules = modules if modules else None
        
        result = _run_bbot_sync(domain, preset=preset, modules=extra_modules, timeout_minutes=10)
        
        # Categorize findings
        if result["success"]:
            technologies = []
            urls = []
            vulnerabilities = []
            
            for event in result.get("results", []):
                if isinstance(event, dict):
                    event_type = event.get("type", "")
                    if "TECHNOLOGY" in event_type:
                        technologies.append(event.get("data", ""))
                    elif "URL" in event_type:
                        urls.append(event.get("data", ""))
                    elif "VULNERABILITY" in event_type or "FINDING" in event_type:
                        vulnerabilities.append(event.get("data", ""))
            
            result["analysis"] = {
                "technologies": technologies,
                "urls_found": len(urls),
                "potential_issues": vulnerabilities
            }
        
        return json.dumps(result, indent=2, default=str)
    
    async def _arun(
        self,
        domain: str,
        modules: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run web recon asynchronously."""
        # Use web-basic preset with optional additional modules
        preset = "web-basic"
        extra_modules = modules if modules else None
        
        result = await _run_bbot_async(domain, preset=preset, modules=extra_modules, timeout_minutes=10)
        
        if result["success"]:
            technologies = []
            urls = []
            vulnerabilities = []
            
            for event in result.get("results", []):
                if isinstance(event, dict):
                    event_type = event.get("type", "")
                    if "TECHNOLOGY" in event_type:
                        technologies.append(event.get("data", ""))
                    elif "URL" in event_type:
                        urls.append(event.get("data", ""))
                    elif "VULNERABILITY" in event_type or "FINDING" in event_type:
                        vulnerabilities.append(event.get("data", ""))
            
            result["analysis"] = {
                "technologies": technologies,
                "urls_found": len(urls),
                "potential_issues": vulnerabilities
            }
        
        return json.dumps(result, indent=2, default=str)


# =============================================================================
# Email Harvesting Tool
# =============================================================================

class BbotEmailTool(BaseTool):
    """
    Harvest email addresses from a target domain using bbot.
    
    Uses the email-enum preset with passive sources:
    - emailformat.com patterns
    - hunter.io database
    - Public breach databases
    - Website scraping
    """
    
    name: str = "bbot_email_harvest"
    description: str = """Harvest email addresses associated with a domain using passive OSINT sources.
Uses bbot's email-enum preset to discover organizational email patterns and addresses.
Input: domain (e.g., 'example.com')
Returns: List of discovered email addresses and common patterns.
Example usage: Find employee emails for a target organization."""
    args_schema: Type[BaseModel] = BbotEmailInput
    
    def _run(
        self,
        domain: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run email harvesting synchronously."""
        # Use email-enum preset with passive flag requirement
        preset = "email-enum"
        require_flags = ["passive"]
        
        result = _run_bbot_sync(domain, preset=preset, require_flags=require_flags, timeout_minutes=5)
        
        # Extract emails
        if result["success"]:
            emails = []
            for event in result.get("results", []):
                if isinstance(event, dict):
                    if event.get("type") == "EMAIL_ADDRESS":
                        emails.append(event.get("data", ""))
                    elif "@" in str(event.get("data", "")):
                        emails.append(str(event.get("data", "")))
            
            result["emails"] = list(set(emails))
            result["email_count"] = len(result["emails"])
        
        return json.dumps(result, indent=2, default=str)
    
    async def _arun(
        self,
        domain: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run email harvesting asynchronously."""
        # Use email-enum preset with passive flag requirement
        preset = "email-enum"
        require_flags = ["passive"]
        
        result = await _run_bbot_async(domain, preset=preset, require_flags=require_flags, timeout_minutes=5)
        
        if result["success"]:
            emails = []
            for event in result.get("results", []):
                if isinstance(event, dict):
                    if event.get("type") == "EMAIL_ADDRESS":
                        emails.append(event.get("data", ""))
            
            result["emails"] = list(set(emails))
            result["email_count"] = len(result["emails"])
        
        return json.dumps(result, indent=2, default=str)
