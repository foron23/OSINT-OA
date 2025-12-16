# =============================================================================
# OSINT News Aggregator - Amass Tools
# =============================================================================
"""
OWASP Amass integration tools for attack surface mapping and asset discovery.

Amass performs network mapping of attack surfaces and external asset discovery
using open source information gathering and active reconnaissance techniques.

GitHub: https://github.com/owasp-amass/amass
Install: go install -v github.com/owasp-amass/amass/v4/...@master

Provides:
- AmassEnumTool: Passive/active subdomain enumeration
- AmassIntelTool: Discover root domains for an organization
"""

import json
import logging
import asyncio
import subprocess
import shutil
import tempfile
import os
from pathlib import Path
from typing import Optional, Type, List, Any, Dict

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun

logger = logging.getLogger(__name__)

# Default amass binary locations
AMASS_BINARY_PATHS = [
    "amass",
    os.path.expanduser("~/go/bin/amass"),
    "/usr/local/bin/amass",
    "/usr/bin/amass",
]


# =============================================================================
# Input Schemas
# =============================================================================

class AmassEnumInput(BaseModel):
    """Input for Amass subdomain enumeration."""
    domain: str = Field(
        description="Target domain to enumerate subdomains. Example: example.com"
    )
    passive: bool = Field(
        default=True,
        description="Use passive mode only (no active probing). Recommended for stealth."
    )
    timeout: int = Field(
        default=300,
        description="Maximum time in seconds for the enumeration"
    )


class AmassIntelInput(BaseModel):
    """Input for Amass intel discovery."""
    org: str = Field(
        description="Organization name to discover root domains. Example: 'Google LLC'"
    )
    timeout: int = Field(
        default=180,
        description="Maximum time in seconds for intel gathering"
    )


# =============================================================================
# Helper Functions
# =============================================================================

def _find_amass_binary() -> Optional[str]:
    """Find amass binary in common locations."""
    for path in AMASS_BINARY_PATHS:
        if shutil.which(path):
            return path
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _check_amass_available() -> bool:
    """Check if amass is installed and available."""
    return _find_amass_binary() is not None


def _parse_amass_json_output(output_file: str) -> List[Dict[str, Any]]:
    """
    Parse amass JSON output file (NDJSON format).
    
    Args:
        output_file: Path to output file
        
    Returns:
        List of parsed results
    """
    results = []
    
    if not os.path.exists(output_file):
        return results
    
    with open(output_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                results.append(data)
            except json.JSONDecodeError:
                # Plain text line (subdomain name)
                if line and not line.startswith('{'):
                    results.append({"name": line})
    
    return results


async def _run_amass_enum_async(
    domain: str,
    passive: bool = True,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Run amass enum asynchronously and return results.
    
    Args:
        domain: Target domain
        passive: Use passive mode only
        timeout: Maximum execution time
        
    Returns:
        Dictionary with enumeration results
    """
    amass_bin = _find_amass_binary()
    
    if not amass_bin:
        return {
            "success": False,
            "error": "Amass not installed. Install with: go install -v github.com/owasp-amass/amass/v4/...@master",
            "domain": domain
        }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "amass_output.txt")
        
        # Build command
        cmd = [
            amass_bin,
            "enum",
            "-d", domain,
            "-o", output_file,
            "-timeout", str(timeout // 60 + 1),  # Convert to minutes
        ]
        
        if passive:
            cmd.append("-passive")
        
        logger.info(f"Running amass enum for domain: {domain}")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout + 30  # Buffer for startup/shutdown
            )
            
            # Read results from output file
            subdomains = []
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    subdomains = [line.strip() for line in f if line.strip()]
            
            # Also parse stdout for any additional info
            stdout_text = stdout.decode('utf-8', errors='replace')
            
            return {
                "success": True,
                "domain": domain,
                "passive_mode": passive,
                "subdomains": subdomains,
                "subdomain_count": len(subdomains),
                "unique_count": len(set(subdomains))
            }
            
        except asyncio.TimeoutError:
            logger.warning(f"Amass timed out for domain: {domain}")
            
            # Try to get partial results
            subdomains = []
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    subdomains = [line.strip() for line in f if line.strip()]
            
            return {
                "success": False,
                "error": f"Timeout after {timeout}s",
                "domain": domain,
                "partial": True,
                "subdomains": subdomains,
                "subdomain_count": len(subdomains)
            }
        except Exception as e:
            logger.error(f"Amass error: {e}")
            return {
                "success": False,
                "error": str(e),
                "domain": domain
            }


async def _run_amass_intel_async(
    org: str,
    timeout: int = 180
) -> Dict[str, Any]:
    """
    Run amass intel asynchronously to discover root domains.
    
    Args:
        org: Organization name
        timeout: Maximum execution time
        
    Returns:
        Dictionary with discovered domains
    """
    amass_bin = _find_amass_binary()
    
    if not amass_bin:
        return {
            "success": False,
            "error": "Amass not installed. Install with: go install -v github.com/owasp-amass/amass/v4/...@master",
            "organization": org
        }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "amass_intel.txt")
        
        # Build command for intel mode
        cmd = [
            amass_bin,
            "intel",
            "-org", org,
            "-o", output_file,
            "-timeout", str(timeout // 60 + 1),
        ]
        
        logger.info(f"Running amass intel for org: {org}")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout + 30
            )
            
            # Read results
            domains = []
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    domains = [line.strip() for line in f if line.strip()]
            
            return {
                "success": True,
                "organization": org,
                "root_domains": domains,
                "domain_count": len(domains)
            }
            
        except asyncio.TimeoutError:
            logger.warning(f"Amass intel timed out for org: {org}")
            
            domains = []
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    domains = [line.strip() for line in f if line.strip()]
            
            return {
                "success": False,
                "error": f"Timeout after {timeout}s",
                "organization": org,
                "partial": True,
                "root_domains": domains,
                "domain_count": len(domains)
            }
        except Exception as e:
            logger.error(f"Amass intel error: {e}")
            return {
                "success": False,
                "error": str(e),
                "organization": org
            }


# =============================================================================
# LangChain Tools
# =============================================================================

class AmassEnumTool(BaseTool):
    """
    Tool for subdomain enumeration using OWASP Amass.
    
    Amass is the industry-standard tool for attack surface mapping.
    It uses many data sources including:
    - Certificate Transparency logs
    - DNS databases
    - Web archives
    - Search engines
    - And many more passive sources
    
    Features:
    - Passive mode for stealth reconnaissance
    - Active mode for comprehensive discovery
    - High-quality results with deduplication
    """
    
    name: str = "amass_subdomain_enum"
    description: str = """Enumerate subdomains of a target domain using OWASP Amass.

Use this tool for comprehensive subdomain discovery. Amass is the industry standard
for attack surface mapping and uses multiple passive data sources.

Input: domain (e.g., "example.com"), passive mode (default: true), timeout (seconds)
Output: JSON with list of discovered subdomains

Example:
- Input: domain="example.com", passive=true
- Output: {"subdomains": ["www.example.com", "api.example.com", "mail.example.com"], "subdomain_count": 3}

Note: Passive mode is recommended for stealth. Active mode performs DNS bruting and zone transfers.
"""
    
    args_schema: Type[BaseModel] = AmassEnumInput
    
    def _run(
        self,
        domain: str,
        passive: bool = True,
        timeout: int = 300,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run amass enum synchronously."""
        result = asyncio.run(
            _run_amass_enum_async(domain, passive, timeout)
        )
        return json.dumps(result, indent=2)
    
    async def _arun(
        self,
        domain: str,
        passive: bool = True,
        timeout: int = 300,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run amass enum asynchronously."""
        result = await _run_amass_enum_async(domain, passive, timeout)
        return json.dumps(result, indent=2)


class AmassIntelTool(BaseTool):
    """
    Tool for discovering root domains of an organization using Amass intel.
    
    This tool helps identify all domains associated with an organization
    by querying various OSINT sources.
    """
    
    name: str = "amass_intel_discovery"
    description: str = """Discover root domains associated with an organization using Amass intel.

Use this tool when you need to find all domains owned by a specific organization
before performing subdomain enumeration.

Input: organization name (e.g., "Google LLC", "Microsoft Corporation")
Output: JSON with list of root domains discovered

Example:
- Input: org="Tesla Inc"
- Output: {"root_domains": ["tesla.com", "teslamotors.com"], "domain_count": 2}

Note: Organization name should match official registrations for best results.
"""
    
    args_schema: Type[BaseModel] = AmassIntelInput
    
    def _run(
        self,
        org: str,
        timeout: int = 180,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run amass intel synchronously."""
        result = asyncio.run(
            _run_amass_intel_async(org, timeout)
        )
        return json.dumps(result, indent=2)
    
    async def _arun(
        self,
        org: str,
        timeout: int = 180,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run amass intel asynchronously."""
        result = await _run_amass_intel_async(org, timeout)
        return json.dumps(result, indent=2)


# =============================================================================
# Convenience Functions
# =============================================================================

def get_amass_tools() -> List[BaseTool]:
    """Get all Amass tools for use in agents."""
    return [AmassEnumTool(), AmassIntelTool()]


def check_amass_installation() -> Dict[str, Any]:
    """Check if Amass is properly installed."""
    amass_bin = _find_amass_binary()
    available = amass_bin is not None
    
    version = None
    if available:
        try:
            result = subprocess.run(
                [amass_bin, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Version is typically in format "v4.2.0"
            version = result.stdout.strip() or result.stderr.strip()
            if version:
                version = version.split()[-1] if version else None
        except Exception:
            pass
    
    return {
        "tool": "amass",
        "available": available,
        "binary_path": amass_bin,
        "version": version,
        "install_command": "go install -v github.com/owasp-amass/amass/v4/...@master"
    }


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "AmassEnumTool",
    "AmassIntelTool",
    "AmassEnumInput",
    "AmassIntelInput",
    "get_amass_tools",
    "check_amass_installation",
]
