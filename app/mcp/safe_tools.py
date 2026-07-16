"""
app/mcp/safe_tools.py
======================
Sichere, extern exposable MCP-Tools, die KEINE Secrets leaken.

Liefert:
  - provider_env_status : Boolean-Map welche Provider-Keys/URLs konfiguriert sind
  - hive_status         : Hive/Hyve-Konfigurationsstatus, optional Reachability

Diese Tools werden als 'read_safe' klassifiziert und sind in der externen
tools/list-Antwort (mcp_remote.get_tools) frei verfuegbar.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..config import get_settings
from ..services.hive_client import get_hive_client
from ..utils.redaction import safe_provider_status

logger = logging.getLogger("ailinux.mcp.safe_tools")


# =============================================================================
# Tool-Definitionen (extern sichtbar)
# =============================================================================

SAFE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "provider_env_status",
        "description": (
            "Check which AI provider API keys and base URLs are configured on "
            "the server. Returns only boolean presence flags per provider - "
            "never key values, prefixes, or path information. Useful for "
            "diagnosing 'why is provider X not working' without exposing secrets."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "providers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional list of provider IDs to check (e.g. "
                        "['openai', 'anthropic', 'gemini']). If omitted, all "
                        "known providers are checked."
                    ),
                }
            },
        },
        "annotations": {
            "title": "Provider Env Status (Read-Only)",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "hive_status",
        "description": (
            "Check Hive/Hyve integration status. Returns whether an API key is "
            "configured, which environment variable holds it (HIVE_API_KEY or "
            "HYVE_API_KEY), whether a base URL is configured, and optionally "
            "whether the endpoint is reachable. No secret material is returned."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "probe": {
                    "type": "boolean",
                    "description": (
                        "If true, attempt an unauthenticated GET against the "
                        "configured base URL to test reachability. Default: false."
                    ),
                }
            },
        },
        "annotations": {
            "title": "Hive Status (Read-Only)",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,  # Probe trifft externes Netz
        },
    },
]


# =============================================================================
# Handler
# =============================================================================

# Provider-IDs, fuer die wir Status liefern. safe_provider_status() in
# app/utils/redaction.py kennt mehr Provider; hier listen wir die fuer Klienten
# relevanten auf.
_DEFAULT_PROVIDERS: List[str] = [
    "openai",
    "anthropic",
    "gemini",
    "groq",
    "mistral",
    "deepseek",
    "openrouter",
    "cloudflare",
    "github",
    "huggingface",
    "ollama",
    "jina",
    "hive",
]


async def handle_provider_env_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return only boolean presence flags per provider."""
    requested: Optional[List[str]] = args.get("providers") if isinstance(args, dict) else None
    providers = requested if requested else _DEFAULT_PROVIDERS

    # safe_provider_status(providers, *, source=None) — Default: os.environ
    status = safe_provider_status(providers)

    return {
        "ok": True,
        "providers": status,
        "checked": list(status.keys()),
        "note": "Only boolean presence flags. No key values or prefixes are returned.",
    }


async def handle_hive_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return Hive/Hyve presence + optional reachability. No secrets."""
    probe = bool(args.get("probe", False)) if isinstance(args, dict) else False
    client = get_hive_client()
    data = await client.status_async(probe=probe)
    # Defensive: falls irgendwer doch mal was rein-mergt, hier final saeubern.
    safe_keys = {"configured", "base_url_configured", "key_source", "reachable", "error"}
    cleaned = {k: v for k, v in data.items() if k in safe_keys}
    cleaned["ok"] = True
    cleaned["note"] = "No secret material is returned."
    return cleaned


SAFE_HANDLERS: Dict[str, Any] = {
    "provider_env_status": handle_provider_env_status,
    "hive_status": handle_hive_status,
}


__all__ = ["SAFE_TOOLS", "SAFE_HANDLERS", "handle_provider_env_status", "handle_hive_status"]
