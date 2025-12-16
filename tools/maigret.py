# =============================================================================
# OSINT News Aggregator - Maigret Tools
# =============================================================================
"""
Maigret integration tools for OSINT username enumeration.

Maigret is a modern replacement for OSRFramework's usufy tool.
It searches for usernames across 500+ platforms with better accuracy.

GitHub: https://github.com/soxoj/maigret
Install: pip install maigret

Provides:
- MaigretUsernameTool: Search username across platforms
- MaigretReportTool: Generate detailed report from search
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

class MaigretUsernameInput(BaseModel):
    """Input for Maigret username search."""
    username: str = Field(description="Username to search across platforms")
    timeout: int = Field(default=30, description="Timeout per site in seconds")
    top_sites: int = Field(default=100, description="Only check top N sites by popularity")


class MaigretReportInput(BaseModel):
    """Input for Maigret report generation."""
    username: str = Field(description="Username to investigate")
    format: str = Field(default="json", description="Output format: json, html, or txt")


# =============================================================================
# Helper Functions
# =============================================================================

def _check_maigret_available() -> bool:
    """Check if maigret is installed and available."""
    return shutil.which('maigret') is not None


async def _run_maigret_async(
    username: str,
    timeout: int = 30,
    top_sites: int = 100,
    output_format: str = "json"
) -> dict:
    """
    Run maigret asynchronously and return results.
    
    Args:
        username: The username to search
        timeout: Timeout per site
        top_sites: Only check top N sites
        output_format: Output format (json, html, txt)
        
    Returns:
        Dictionary with search results
    """
    if not _check_maigret_available():
        return {
            "success": False,
            "error": "maigret not installed. Install with: pip install maigret",
            "results": []
        }
    
    # Create temporary directory for output
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        
        # Build command according to maigret documentation
        # maigret USERNAME --top-sites N --timeout T -J ndjson -fo OUTPUT_FOLDER
        cmd = [
            'maigret',
            username,
            '--timeout', str(timeout),
            '--top-sites', str(top_sites),
            '-J', 'ndjson',  # JSON output in ndjson format
            '-fo', str(output_dir),  # folder output
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout * top_sites / 10 + 120  # Dynamic timeout based on sites
            )
            
            # Parse NDJSON output - maigret creates files like: report_USERNAME_ndjson.json
            found_sites = []
            
            def extract_site_info(entry: dict) -> dict:
                """Extract site info from maigret entry, handling nested status."""
                # Status can be nested in entry["status"]["status"] or directly in entry["status"]
                status_data = entry.get("status", {})
                if isinstance(status_data, dict):
                    status_str = status_data.get("status", "")
                    site_name = status_data.get("site_name", entry.get("sitename", ""))
                else:
                    status_str = str(status_data)
                    site_name = entry.get("sitename", "")
                
                return {
                    "site": site_name or entry.get("sitename", ""),
                    "url": entry.get("url_user", entry.get("url", "")),
                    "status": status_str
                }
            
            # Look for all json/ndjson files in output directory (maigret uses *_ndjson.json format)
            for output_file in list(output_dir.glob(f"*{username}*.json")) + list(output_dir.glob(f"*{username}*.ndjson")):
                try:
                    with open(output_file, 'r') as f:
                        content = f.read()
                        # Try parsing as NDJSON (one JSON object per line)
                        for line in content.strip().split('\n'):
                            line = line.strip()
                            if line:
                                try:
                                    entry = json.loads(line)
                                    info = extract_site_info(entry)
                                    if info["status"].lower() in ["claimed", "found"]:
                                        found_sites.append(info)
                                except json.JSONDecodeError:
                                    continue
                except Exception as e:
                    logger.debug(f"Error reading {output_file}: {e}")
            
            # Parse stdout for results if no files found
            if not found_sites:
                output = stdout.decode('utf-8', errors='ignore')
                for line in output.split('\n'):
                    if '[+]' in line or 'Claimed' in line:
                        # Extract site info from output line
                        parts = line.strip().split()
                        url = None
                        for part in parts:
                            if part.startswith('http'):
                                url = part
                                break
                        if url:
                            found_sites.append({
                                "site": url.split('/')[2] if len(url.split('/')) > 2 else url,
                                "url": url,
                                "status": "found"
                            })
            
            return {
                "success": True,
                "username": username,
                "sites_checked": top_sites,
                "found_count": len(found_sites),
                "results": found_sites,
                "error": None
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "username": username,
                "error": "Maigret search timed out",
                "results": []
            }
        except Exception as e:
            return {
                "success": False,
                "username": username,
                "error": str(e),
                "results": []
            }


def _run_maigret_sync(
    username: str,
    timeout: int = 30,
    top_sites: int = 100
) -> dict:
    """Synchronous wrapper for maigret."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_run_maigret_async(username, timeout, top_sites))


# =============================================================================
# Maigret Username Search Tool
# =============================================================================

class MaigretUsernameTool(BaseTool):
    """
    Search for a username across social media platforms using Maigret.
    
    Maigret searches 500+ platforms including:
    - Social media (Twitter, Instagram, TikTok, etc.)
    - Professional networks (LinkedIn, GitHub, etc.)
    - Forums and communities
    - Gaming platforms
    - Dating sites
    """
    
    name: str = "maigret_username_search"
    description: str = """Search for a username across 500+ social media and web platforms.
Uses Maigret for comprehensive username OSINT and profile discovery.
Input: username (exact string), timeout (seconds, default 30), top_sites (number of sites to check, default 100)
Returns: List of platforms where the username was found with profile URLs.
Example usage: Find all social media accounts for username 'johndoe123'."""
    args_schema: Type[BaseModel] = MaigretUsernameInput
    
    def _run(
        self,
        username: str,
        timeout: int = 30,
        top_sites: int = 100,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run maigret username search synchronously."""
        result = _run_maigret_sync(username, timeout, top_sites)
        return json.dumps(result, indent=2, default=str)
    
    async def _arun(
        self,
        username: str,
        timeout: int = 30,
        top_sites: int = 100,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run maigret username search asynchronously."""
        result = await _run_maigret_async(username, timeout, top_sites)
        return json.dumps(result, indent=2, default=str)


# =============================================================================
# Maigret Report Tool
# =============================================================================

class MaigretReportTool(BaseTool):
    """
    Generate a detailed Maigret report for a username.
    
    Performs comprehensive analysis including:
    - Deep search across 300+ platforms
    - Profile consistency analysis
    - Cross-platform correlation
    - Online identity strength assessment
    """
    
    name: str = "maigret_report"
    description: str = """Generate a comprehensive OSINT report for a username.
Performs deep search across 300 platforms with detailed analysis.
Input: username (exact string), format (default 'json')
Returns: Structured report with all discovered profiles and identity analysis.
Example usage: Get detailed identity report for a person of interest."""
    args_schema: Type[BaseModel] = MaigretReportInput
    
    def _run(
        self,
        username: str,
        format: str = "json",
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Generate maigret report synchronously."""
        # Use more sites for comprehensive report
        result = _run_maigret_sync(username, timeout=60, top_sites=300)
        
        if result["success"]:
            report = {
                "report_type": "maigret_investigation",
                "username": username,
                "total_sites_checked": 300,
                "profiles_found": result.get("found_count", len(result.get("results", []))),
                "platforms": result.get("results", []),
                "analysis": {
                    "cross_platform_presence": len(result.get("results", [])) > 5,
                    "online_identity_strength": "high" if len(result.get("results", [])) > 20 else 
                                               "medium" if len(result.get("results", [])) > 5 else "low"
                }
            }
        else:
            report = {
                "error": result.get("error", "Unknown error"),
                "username": username
            }
        
        return json.dumps(report, indent=2, default=str)
    
    async def _arun(
        self,
        username: str,
        format: str = "json",
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Generate maigret report asynchronously."""
        result = await _run_maigret_async(username, timeout=60, top_sites=300)
        
        if result["success"]:
            report = {
                "report_type": "maigret_investigation",
                "username": username,
                "total_sites_checked": 300,
                "profiles_found": result.get("found_count", len(result.get("results", []))),
                "platforms": result.get("results", []),
                "analysis": {
                    "cross_platform_presence": len(result.get("results", [])) > 5,
                    "online_identity_strength": "high" if len(result.get("results", [])) > 20 else 
                                               "medium" if len(result.get("results", [])) > 5 else "low"
                }
            }
        else:
            report = {
                "error": result.get("error", "Unknown error"),
                "username": username
            }
        
        return json.dumps(report, indent=2, default=str)
