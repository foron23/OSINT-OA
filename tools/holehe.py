# =============================================================================
# OSINT News Aggregator - Holehe Tools
# =============================================================================
"""
Holehe integration tools for OSINT email enumeration.

Holehe checks if an email is registered on various websites without
alerting the target or triggering security measures.

GitHub: https://github.com/megadose/holehe
Install: pip install holehe

Provides:
- HoleheEmailTool: Check email registration across 100+ platforms
"""

import json
import logging
import asyncio
import subprocess
import shutil
import tempfile
import re
from pathlib import Path
from typing import Optional, Type, List, Any, Dict

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun

logger = logging.getLogger(__name__)


# =============================================================================
# Input Schemas
# =============================================================================

class HoleheEmailInput(BaseModel):
    """Input for Holehe email search."""
    email: str = Field(
        description="Email address to check across platforms. Example: user@example.com"
    )
    timeout: int = Field(
        default=15,
        description="Timeout per site in seconds"
    )
    only_used: bool = Field(
        default=True,
        description="Only return sites where the email is registered"
    )


# =============================================================================
# Helper Functions
# =============================================================================

def _check_holehe_available() -> bool:
    """Check if holehe is installed and available."""
    return shutil.which('holehe') is not None


def _parse_holehe_output(output: str) -> Dict[str, Any]:
    """
    Parse holehe CLI output to structured data.
    
    Holehe outputs lines like:
    [+] site.com (email used)
    [-] site.com (email not used)
    [x] site.com (rate limited)
    
    Args:
        output: Raw CLI output
        
    Returns:
        Structured results dictionary
    """
    results = {
        "used": [],
        "not_used": [],
        "rate_limited": [],
        "errors": []
    }
    
    # Patterns for different result types
    used_pattern = re.compile(r'\[\+\]\s+(\S+)')
    not_used_pattern = re.compile(r'\[-\]\s+(\S+)')
    rate_limited_pattern = re.compile(r'\[x\]\s+(\S+)')
    
    for line in output.split('\n'):
        line = line.strip()
        
        # Match used sites
        match = used_pattern.match(line)
        if match:
            results["used"].append(match.group(1))
            continue
            
        # Match not used sites
        match = not_used_pattern.match(line)
        if match:
            results["not_used"].append(match.group(1))
            continue
            
        # Match rate limited sites
        match = rate_limited_pattern.match(line)
        if match:
            results["rate_limited"].append(match.group(1))
            continue
    
    return results


async def _run_holehe_async(
    email: str,
    timeout: int = 15,
    only_used: bool = True
) -> Dict[str, Any]:
    """
    Run holehe asynchronously and return results.
    
    Args:
        email: The email to check
        timeout: Timeout per site
        only_used: Only return used sites
        
    Returns:
        Dictionary with search results
    """
    if not _check_holehe_available():
        return {
            "success": False,
            "error": "Holehe not installed. Install with: pip install holehe",
            "email": email
        }
    
    # Build command
    cmd = [
        "holehe",
        email,
        "--no-clear",
        "--no-color",
        "-T", str(timeout)
    ]
    
    if only_used:
        cmd.append("--only-used")
    
    logger.info(f"Running holehe for email: {email}")
    logger.debug(f"Command: {' '.join(cmd)}")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait with overall timeout (sites * per-site timeout + buffer)
        overall_timeout = 200  # ~120 sites
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=overall_timeout
        )
        
        output = stdout.decode('utf-8', errors='replace')
        error_output = stderr.decode('utf-8', errors='replace')
        
        # Parse the output
        parsed = _parse_holehe_output(output)
        
        return {
            "success": True,
            "email": email,
            "sites_used": parsed["used"],
            "sites_used_count": len(parsed["used"]),
            "sites_not_used_count": len(parsed["not_used"]) if not only_used else "N/A",
            "rate_limited_count": len(parsed["rate_limited"]),
            "raw_output": output if len(parsed["used"]) == 0 else None
        }
        
    except asyncio.TimeoutError:
        logger.warning(f"Holehe timed out for email: {email}")
        return {
            "success": False,
            "error": f"Timeout after {overall_timeout}s",
            "email": email,
            "partial": True
        }
    except Exception as e:
        logger.error(f"Holehe error: {e}")
        return {
            "success": False,
            "error": str(e),
            "email": email
        }


# =============================================================================
# LangChain Tools
# =============================================================================

class HoleheEmailTool(BaseTool):
    """
    Tool for checking email registration across platforms using Holehe.
    
    Holehe uses password recovery mechanisms to check if an email
    is registered on various websites, without alerting the target.
    
    Features:
    - Checks 100+ popular websites
    - Non-intrusive (uses password recovery endpoints)
    - Returns list of sites where email is registered
    """
    
    name: str = "holehe_email_check"
    description: str = """Check if an email address is registered on various websites.
    
Use this tool to discover what online services/platforms are associated with an email address.
This helps identify the online presence and accounts linked to an email.

Input: email address (e.g., "user@example.com")
Output: JSON with list of websites where the email is registered

Example usage:
- Input: "john.doe@gmail.com"
- Output: {"sites_used": ["twitter.com", "spotify.com", "github.com"], "sites_used_count": 3}
"""
    
    args_schema: Type[BaseModel] = HoleheEmailInput
    
    def _run(
        self,
        email: str,
        timeout: int = 15,
        only_used: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run holehe synchronously."""
        result = asyncio.run(
            _run_holehe_async(email, timeout, only_used)
        )
        return json.dumps(result, indent=2)
    
    async def _arun(
        self,
        email: str,
        timeout: int = 15,
        only_used: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run holehe asynchronously."""
        result = await _run_holehe_async(email, timeout, only_used)
        return json.dumps(result, indent=2)


# =============================================================================
# Convenience Functions
# =============================================================================

def get_holehe_tools() -> List[BaseTool]:
    """Get all Holehe tools for use in agents."""
    return [HoleheEmailTool()]


def check_holehe_installation() -> Dict[str, Any]:
    """Check if Holehe is properly installed."""
    available = _check_holehe_available()
    
    version = None
    if available:
        try:
            result = subprocess.run(
                ["holehe", "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Extract version from help output
            if "holehe v" in result.stdout:
                version = result.stdout.split("holehe v")[1].split()[0]
        except Exception:
            pass
    
    return {
        "tool": "holehe",
        "available": available,
        "version": version,
        "install_command": "pip install holehe"
    }


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "HoleheEmailTool",
    "HoleheEmailInput",
    "get_holehe_tools",
    "check_holehe_installation",
]
