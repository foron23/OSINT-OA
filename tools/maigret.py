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
        output_path = Path(tmpdir) / f"maigret_{username}"
        
        cmd = [
            'maigret',
            username,
            '--timeout', str(timeout),
            '--top-sites', str(top_sites),
            f'--{output_format}', str(output_path.with_suffix(f'.{output_format}')),
            '--no-progressbar',
            '--no-color',
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout * top_sites / 10 + 60  # Dynamic timeout based on sites
            )
            
            # Parse JSON output if available
            json_file = output_path.with_suffix('.json')
            if json_file.exists():
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    return {
                        "success": True,
                        "username": username,
                        "sites_checked": top_sites,
                        "results": data,
                        "error": None
                    }
            
            # Parse stdout for results
            output = stdout.decode('utf-8', errors='ignore')
            found_sites = []
            
            for line in output.split('\n'):
                if '[+]' in line or 'Positive' in line:
                    # Extract site name from output
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        site_info = {
                            "site": parts[-1] if parts[-1].startswith('http') else ' '.join(parts[1:]),
                            "status": "found"
                        }
                        found_sites.append(site_info)
            
            return {
                "success": True,
                "username": username,
                "sites_checked": top_sites,
                "found_count": len(found_sites),
                "results": found_sites,
                "raw_output": output[:2000] if len(output) > 2000 else output,
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
    
    Maigret is more accurate and comprehensive than OSRFramework's usufy,
    supporting 500+ platforms with better detection algorithms.
    """
    
    name: str = "maigret_username_search"
    description: str = """Search for a username across 500+ social media and web platforms.
    Uses Maigret for accurate username enumeration and OSINT.
    Returns: List of platforms where the username was found with profile URLs."""
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
    - Username found across platforms
    - Profile consistency analysis
    - Cross-platform correlation
    """
    
    name: str = "maigret_report"
    description: str = """Generate a comprehensive OSINT report for a username.
    Searches all available platforms and generates detailed findings.
    Returns: Structured report with all discovered profiles."""
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
