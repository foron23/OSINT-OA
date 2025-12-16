# =============================================================================
# OSINT News Aggregator - PhoneInfoga Tools
# =============================================================================
"""
PhoneInfoga integration tools for phone number OSINT.

PhoneInfoga is an advanced framework for scanning phone numbers using
only free resources. It retrieves standard information like country,
carrier, line type, and searches for footprints on social media.

GitHub: https://github.com/sundowndev/phoneinfoga
Install: Download binary from releases or use install script

Provides:
- PhoneInfogaScanTool: Scan a phone number for OSINT information
"""

import json
import logging
import asyncio
import subprocess
import shutil
import os
from typing import Optional, Type, List, Any, Dict

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun

logger = logging.getLogger(__name__)

# Default phoneinfoga binary locations
PHONEINFOGA_BINARY_PATHS = [
    "phoneinfoga",
    "/usr/local/bin/phoneinfoga",
    "/usr/bin/phoneinfoga",
    os.path.expanduser("~/phoneinfoga"),
    "./phoneinfoga",
]


# =============================================================================
# Input Schemas
# =============================================================================

class PhoneInfogaScanInput(BaseModel):
    """Input for PhoneInfoga phone number scan."""
    phone_number: str = Field(
        description="Phone number to scan in E.164 or international format. "
                    "Example: '+34612345678' or '+1-555-123-4567'"
    )
    timeout: int = Field(
        default=60,
        description="Maximum time in seconds for the scan"
    )


# =============================================================================
# Helper Functions
# =============================================================================

def _find_phoneinfoga_binary() -> Optional[str]:
    """Find phoneinfoga binary in common locations."""
    for path in PHONEINFOGA_BINARY_PATHS:
        if shutil.which(path):
            return path
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _check_phoneinfoga_available() -> bool:
    """Check if phoneinfoga is installed and available."""
    return _find_phoneinfoga_binary() is not None


def _parse_phoneinfoga_output(output: str) -> Dict[str, Any]:
    """
    Parse phoneinfoga scan output.
    
    The output contains structured information about the phone number
    including country, carrier, and scan results from various sources.
    
    Args:
        output: Raw CLI output
        
    Returns:
        Parsed results dictionary
    """
    result = {
        "raw_output": output,
        "country": None,
        "carrier": None,
        "line_type": None,
        "valid": None,
        "local_format": None,
        "international_format": None,
        "country_code": None,
        "scanners": {}
    }
    
    lines = output.split('\n')
    current_scanner = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Parse basic info
        if "Country:" in line:
            result["country"] = line.split(":", 1)[1].strip()
        elif "Carrier:" in line:
            result["carrier"] = line.split(":", 1)[1].strip()
        elif "Line type:" in line or "LineType:" in line:
            result["line_type"] = line.split(":", 1)[1].strip()
        elif "Valid:" in line:
            result["valid"] = "true" in line.lower()
        elif "Local format:" in line:
            result["local_format"] = line.split(":", 1)[1].strip()
        elif "International format:" in line or "E164:" in line:
            result["international_format"] = line.split(":", 1)[1].strip()
        elif "Country code:" in line:
            result["country_code"] = line.split(":", 1)[1].strip()
        
        # Detect scanner sections
        if "Running scanner" in line:
            scanner_name = line.split("Running scanner")[-1].strip().strip(".")
            current_scanner = scanner_name
            result["scanners"][scanner_name] = {"results": []}
        elif current_scanner and ("found" in line.lower() or "result" in line.lower()):
            result["scanners"][current_scanner]["results"].append(line)
    
    return result


async def _run_phoneinfoga_async(
    phone_number: str,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    Run phoneinfoga scan asynchronously and return results.
    
    Args:
        phone_number: The phone number to scan (E.164 format recommended)
        timeout: Maximum execution time
        
    Returns:
        Dictionary with scan results
    """
    phoneinfoga_bin = _find_phoneinfoga_binary()
    
    if not phoneinfoga_bin:
        return {
            "success": False,
            "error": "PhoneInfoga not installed. Install from: https://github.com/sundowndev/phoneinfoga/releases",
            "phone_number": phone_number
        }
    
    # Normalize phone number (ensure it starts with +)
    normalized_number = phone_number.strip()
    if not normalized_number.startswith('+'):
        # Try to add + if it looks like an international number
        if normalized_number.startswith('00'):
            normalized_number = '+' + normalized_number[2:]
        elif len(normalized_number) > 10:
            normalized_number = '+' + normalized_number
    
    # Build command
    cmd = [
        phoneinfoga_bin,
        "scan",
        "-n", normalized_number
    ]
    
    logger.info(f"Running phoneinfoga scan for: {normalized_number}")
    logger.debug(f"Command: {' '.join(cmd)}")
    
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout
        )
        
        output = stdout.decode('utf-8', errors='replace')
        error_output = stderr.decode('utf-8', errors='replace')
        
        # Parse the output
        parsed = _parse_phoneinfoga_output(output)
        
        # Check for errors in output
        if "error" in output.lower() or proc.returncode != 0:
            if "invalid" in output.lower():
                return {
                    "success": False,
                    "error": "Invalid phone number format",
                    "phone_number": phone_number,
                    "hint": "Use E.164 format: +[country_code][number] e.g., +34612345678"
                }
        
        return {
            "success": True,
            "phone_number": phone_number,
            "normalized": normalized_number,
            "country": parsed["country"],
            "carrier": parsed["carrier"],
            "line_type": parsed["line_type"],
            "valid": parsed["valid"],
            "local_format": parsed["local_format"],
            "international_format": parsed["international_format"],
            "country_code": parsed["country_code"],
            "scanners_run": list(parsed["scanners"].keys()),
            "scanner_results": parsed["scanners"]
        }
        
    except asyncio.TimeoutError:
        logger.warning(f"PhoneInfoga timed out for: {phone_number}")
        return {
            "success": False,
            "error": f"Timeout after {timeout}s",
            "phone_number": phone_number,
            "partial": True
        }
    except Exception as e:
        logger.error(f"PhoneInfoga error: {e}")
        return {
            "success": False,
            "error": str(e),
            "phone_number": phone_number
        }


# =============================================================================
# LangChain Tools
# =============================================================================

class PhoneInfogaScanTool(BaseTool):
    """
    Tool for scanning phone numbers using PhoneInfoga.
    
    PhoneInfoga provides OSINT information about phone numbers including:
    - Country and carrier identification
    - Line type (mobile/landline/VoIP)
    - Format validation and normalization
    - Social media footprint scanning
    
    Features:
    - No API keys required
    - Uses free resources only
    - Validates and normalizes phone numbers
    """
    
    name: str = "phoneinfoga_scan"
    description: str = """Scan a phone number for OSINT information using PhoneInfoga.

Use this tool to gather intelligence about a phone number including country,
carrier, line type, and potential social media presence.

Input: phone_number in E.164 or international format (e.g., "+34612345678", "+1-555-123-4567")
Output: JSON with country, carrier, line type, and scanner results

Example:
- Input: phone_number="+34612345678"
- Output: {"country": "Spain", "carrier": "Movistar", "line_type": "mobile", ...}

Important:
- Use E.164 format (+[country_code][number]) for best results
- Spanish numbers: +34XXXXXXXXX
- US numbers: +1XXXXXXXXXX
- UK numbers: +44XXXXXXXXXX
"""
    
    args_schema: Type[BaseModel] = PhoneInfogaScanInput
    
    def _run(
        self,
        phone_number: str,
        timeout: int = 60,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run phoneinfoga scan synchronously."""
        result = asyncio.run(
            _run_phoneinfoga_async(phone_number, timeout)
        )
        return json.dumps(result, indent=2)
    
    async def _arun(
        self,
        phone_number: str,
        timeout: int = 60,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Run phoneinfoga scan asynchronously."""
        result = await _run_phoneinfoga_async(phone_number, timeout)
        return json.dumps(result, indent=2)


# =============================================================================
# Convenience Functions
# =============================================================================

def get_phoneinfoga_tools() -> List[BaseTool]:
    """Get all PhoneInfoga tools for use in agents."""
    return [PhoneInfogaScanTool()]


def check_phoneinfoga_installation() -> Dict[str, Any]:
    """Check if PhoneInfoga is properly installed."""
    phoneinfoga_bin = _find_phoneinfoga_binary()
    available = phoneinfoga_bin is not None
    
    version = None
    if available:
        try:
            result = subprocess.run(
                [phoneinfoga_bin, "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            version = result.stdout.strip()
        except Exception:
            pass
    
    return {
        "tool": "phoneinfoga",
        "available": available,
        "binary_path": phoneinfoga_bin,
        "version": version,
        "install_command": "curl -sSL https://raw.githubusercontent.com/sundowndev/phoneinfoga/master/support/scripts/install | bash"
    }


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "PhoneInfogaScanTool",
    "PhoneInfogaScanInput",
    "get_phoneinfoga_tools",
    "check_phoneinfoga_installation",
]
