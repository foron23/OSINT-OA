# =============================================================================
# OSINT News Aggregator - bbot Tools
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
    modules: Optional[List[str]] = None,
    flags: Optional[List[str]] = None,
    output_modules: Optional[List[str]] = None,
    timeout_minutes: int = 10
) -> dict:
    """
    Run bbot asynchronously and return results.
    
    Args:
        target: Target domain or IP
        modules: Specific modules to run
        flags: Additional flags (e.g., passive-only)
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
        
        cmd = [
            'bbot',
            '-t', target,
            '-o', str(output_dir),
            '--silent',
            '-y',  # Yes to all prompts
        ]
        
        if modules:
            cmd.extend(['-m'] + modules)
        
        if flags:
            cmd.extend(['-f'] + flags)
        
        # Always output JSON
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
            json_output = output_dir / "output.json"
            ndjson_output = output_dir / "output.ndjson"
            
            results = []
            
            # Try to read NDJSON (newline-delimited JSON)
            if ndjson_output.exists():
                with open(ndjson_output, 'r') as f:
                    for line in f:
                        try:
                            results.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            elif json_output.exists():
                with open(json_output, 'r') as f:
                    results = json.load(f)
            
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
                "modules": modules or "default",
                "events_found": len(results),
                "results": results[:100],  # Limit results
                "error": None
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "target": target,
                "error": f"bbot scan timed out after {timeout_minutes} minutes",
                "results": []
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
    modules: Optional[List[str]] = None,
    flags: Optional[List[str]] = None,
    timeout_minutes: int = 10
) -> dict:
    """Synchronous wrapper for bbot."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        _run_bbot_async(target, modules, flags, timeout_minutes=timeout_minutes)
    )


# =============================================================================
# Subdomain Enumeration Tool
# =============================================================================

class BbotSubdomainTool(BaseTool):
    """
    Enumerate subdomains of a target domain using bbot.
    
    Uses multiple sources including:
    - DNS bruteforce
    - Certificate transparency logs
    - Wayback Machine
    - Public datasets
    - Search engines
    """
    
    name: str = "bbot_subdomain_enum"
    description: str = """Enumerate subdomains of a target domain.
    Uses multiple passive and active sources to discover subdomains.
    Returns: List of discovered subdomains with their status."""
    args_schema: Type[BaseModel] = BbotSubdomainInput
    
    def _run(
        self,
        domain: str,
        passive_only: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run subdomain enumeration synchronously."""
        modules = ["subdomains"]
        flags = ["passive"] if passive_only else None
        
        result = _run_bbot_sync(domain, modules=modules, flags=flags, timeout_minutes=5)
        
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
        modules = ["subdomains"]
        flags = ["passive"] if passive_only else None
        
        result = await _run_bbot_async(domain, modules=modules, flags=flags, timeout_minutes=5)
        
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
    
    Discovers:
    - Web technologies
    - Exposed endpoints
    - API endpoints
    - Sensitive files
    """
    
    name: str = "bbot_web_recon"
    description: str = """Perform web reconnaissance on a target domain.
    Discovers web technologies, exposed endpoints, and sensitive files.
    Returns: Web reconnaissance findings including technologies and endpoints."""
    args_schema: Type[BaseModel] = BbotDomainInput
    
    def _run(
        self,
        domain: str,
        modules: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run web recon synchronously."""
        if modules is None:
            modules = ["httpx", "wayback", "nuclei"]
        
        result = _run_bbot_sync(domain, modules=modules, timeout_minutes=10)
        
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
        if modules is None:
            modules = ["httpx", "wayback", "nuclei"]
        
        result = await _run_bbot_async(domain, modules=modules, timeout_minutes=10)
        
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
    
    Sources include:
    - Website scraping
    - WHOIS records
    - Certificate transparency
    - Public databases
    """
    
    name: str = "bbot_email_harvest"
    description: str = """Harvest email addresses associated with a domain.
    Uses multiple passive sources to discover organizational emails.
    Returns: List of discovered email addresses."""
    args_schema: Type[BaseModel] = BbotEmailInput
    
    def _run(
        self,
        domain: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run email harvesting synchronously."""
        modules = ["emailformat", "skymem", "hunter"]
        flags = ["passive", "emails"]
        
        result = _run_bbot_sync(domain, modules=modules, flags=flags, timeout_minutes=5)
        
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
        modules = ["emailformat", "skymem", "hunter"]
        flags = ["passive", "emails"]
        
        result = await _run_bbot_async(domain, modules=modules, flags=flags, timeout_minutes=5)
        
        if result["success"]:
            emails = []
            for event in result.get("results", []):
                if isinstance(event, dict):
                    if event.get("type") == "EMAIL_ADDRESS":
                        emails.append(event.get("data", ""))
            
            result["emails"] = list(set(emails))
            result["email_count"] = len(result["emails"])
        
        return json.dumps(result, indent=2, default=str)
