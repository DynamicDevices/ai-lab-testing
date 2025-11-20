"""
Foundries VPN Documentation Resource Provider

Provides access to Foundries VPN setup and troubleshooting documentation.

Copyright (C) 2025 Dynamic Devices Ltd
License: GPL-3.0-or-later
"""

from pathlib import Path
from typing import Any, Dict, Optional

from lab_testing.utils.logger import get_logger

logger = get_logger()

# Path to docs directory (relative to project root)
DOCS_DIR = Path(__file__).parent.parent.parent / "docs"


def get_foundries_vpn_documentation(doc_type: str = "clean_installation") -> Dict[str, Any]:
    """
    Get Foundries VPN documentation content.

    Args:
        doc_type: Type of documentation to retrieve:
            - "clean_installation": Complete setup guide (FOUNDRIES_VPN_CLEAN_INSTALLATION.md)
            - "troubleshooting": Troubleshooting guide (FOUNDRIES_VPN_TROUBLESHOOTING.md)
            - "all": All Foundries VPN documentation files

    Returns:
        Dictionary with documentation content
    """
    try:
        if doc_type == "clean_installation":
            doc_path = DOCS_DIR / "FOUNDRIES_VPN_CLEAN_INSTALLATION.md"
            if doc_path.exists():
                content = doc_path.read_text()
                return {
                    "success": True,
                    "doc_type": "clean_installation",
                    "title": "Foundries VPN Clean Installation Guide",
                    "description": "Complete setup guide for a clean Foundries VPN installation with device-to-device communication enabled",
                    "content": content,
                    "file_path": str(doc_path),
                }
            return {
                "success": False,
                "error": f"Documentation file not found: {doc_path}",
            }

        elif doc_type == "troubleshooting":
            doc_path = DOCS_DIR / "FOUNDRIES_VPN_TROUBLESHOOTING.md"
            if doc_path.exists():
                content = doc_path.read_text()
                return {
                    "success": True,
                    "doc_type": "troubleshooting",
                    "title": "Foundries VPN Troubleshooting Guide",
                    "description": "Common issues, root causes, and fixes for Foundries VPN setup",
                    "content": content,
                    "file_path": str(doc_path),
                }
            return {
                "success": False,
                "error": f"Documentation file not found: {doc_path}",
            }

        elif doc_type == "all":
            # Return list of all Foundries VPN docs
            docs = {}
            doc_files = [
                ("clean_installation", "FOUNDRIES_VPN_CLEAN_INSTALLATION.md"),
                ("troubleshooting", "FOUNDRIES_VPN_TROUBLESHOOTING.md"),
            ]

            for key, filename in doc_files:
                doc_path = DOCS_DIR / filename
                if doc_path.exists():
                    docs[key] = {
                        "title": filename.replace("FOUNDRIES_VPN_", "").replace(".md", "").replace("_", " ").title(),
                        "file_path": str(doc_path),
                        "exists": True,
                    }
                else:
                    docs[key] = {
                        "file_path": str(doc_path),
                        "exists": False,
                    }

            return {
                "success": True,
                "doc_type": "all",
                "available_docs": docs,
                "description": "List of available Foundries VPN documentation files",
            }

        else:
            return {
                "success": False,
                "error": f"Unknown documentation type: {doc_type}",
                "available_types": ["clean_installation", "troubleshooting", "all"],
            }

    except Exception as e:
        logger.error(f"Failed to load Foundries VPN documentation: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to load documentation: {e!s}",
        }

