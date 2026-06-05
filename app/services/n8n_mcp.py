from __future__ import annotations

import logging
import re
import json as _stdlib_json
import os
import time

import httpx
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.services.n8n_client import n8n_client

logger = logging.getLogger("ailinux.n8n.mcp")


def _slugify_path(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    slug = slug.strip("-")
    return slug or "workflow"


def _normalize_wordpress_endpoint(url: Optional[str]) -> str:
    """Ensure we post to the WordPress posts endpoint."""
    if not url:
        return "https://ailinux.me/wp-json/wp/v2/posts"
    clean = str(url).rstrip("/")
    if "/wp-json/wp/v2/" in clean:
        return clean
    return f"{clean}/wp-json/wp/v2/posts"


def _build_wordpress_workflow(
    *,
    name: str,
    webhook_path: str,
    wordpress_url: str,
    credential_id: Optional[str],
    status: str,
    categories: List[int],
    include_source_link: bool,
    activate: bool,
    description: Optional[str],
) -> Dict[str, Any]:
    """Construct a minimal webhook -> WordPress post workflow."""
    content_expr = "={{$json.content || ''}}"
    if include_source_link:
        content_expr = (
            "={{($json.content || '') + "
            "($json.source_url ? `\\n\\n<p><strong>Quelle:</strong> "
            "<a href=\\\"${$json.source_url}\\\" target=\\\"_blank\\\">${$json.source_url}</a></p>` : '')}}"
        )

    body_params = {
        "title": "={{$json.title || 'Untitled'}}",
        "content": content_expr,
        "status": f"={{$json.status || '{status}'}}",
        "categories": f"={{$json.categories || {json_dumps(categories or [])}}}",
    }

    nodes: List[Dict[str, Any]] = [
        {
            "name": "Webhook Trigger",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 1,
            "position": [200, 300],
            "parameters": {
                "path": webhook_path,
                "httpMethod": "POST",
                "responseMode": "onReceived",
            },
        },
        {
            "name": "Post to WordPress",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 1,
            "position": [520, 300],
            "parameters": {
                "url": wordpress_url,
                "method": "POST",
                "authentication": "genericCredentialType",
                "genericAuthType": "httpBasicAuth",
                "sendBody": True,
                "jsonParameters": True,
                "options": {"redirect": {"followRedirects": True}},
                "bodyParametersJson": json_dumps(body_params),
            },
        },
        {
            "name": "Respond",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1,
            "position": [820, 300],
            "parameters": {
                "responseMode": "lastNode",
                "options": {
                    "responseContentType": "application/json",
                },
            },
        },
    ]

    if credential_id:
        nodes[1]["credentials"] = {
            "httpBasicAuth": {"id": credential_id, "name": "WordPress"},
        }

    workflow = {
        "name": name,
        "active": activate,
        "nodes": nodes,
        "connections": {
            "Webhook Trigger": {"main": [[{"node": "Post to WordPress", "type": "main", "index": 0}]]},
            "Post to WordPress": {"main": [[{"node": "Respond", "type": "main", "index": 0}]]},
        },
        "settings": {},
        "staticData": None,
        "versionId": f"v-{int(time.time())}",
    }

    if description:
        workflow["notesInFlow"] = [
            {
                "id": "note-1",
                "name": "Notes",
                "type": "n8n-nodes-base.stickyNote",
                "typeVersion": 1,
                "position": [380, 120],
                "parameters": {"content": description},
            }
        ]

    return workflow


def json_dumps(obj: Any) -> str:
    """Compact JSON dump without spaces (n8n expects a string)."""
    import json

    return json.dumps(obj, separators=(",", ":"))


async def handle_n8n_workflow_create(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a WordPress posting workflow in n8n via API (webhook -> HTTP request).

    Parameters:
    - name: workflow name
    - webhook_path: path after /webhook/ (auto-slugged if omitted)
    - wordpress_url: base site URL or full posts endpoint (defaults to settings or ailinux.me)
    - credential_id: n8n credential ID for WordPress basic auth
    - status: publish|draft|private (default: publish)
    - categories: list of WordPress category IDs
    - include_source_link: append source_url as link to content
    - activate: whether to activate the workflow immediately
    - description: optional sticky note text stored in the workflow
    """
    settings = get_settings()
    name = arguments.get("name") or "TriForce WordPress Autopost"
    webhook_path = arguments.get("webhook_path") or f"{_slugify_path(name)}-{int(time.time())}"
    wordpress_url = _normalize_wordpress_endpoint(
        arguments.get("wordpress_url") or (str(settings.wordpress_url) if settings.wordpress_url else None)
    )
    credential_id = arguments.get("credential_id")
    status = arguments.get("status") or "publish"
    categories = arguments.get("categories") or []
    include_source_link = bool(arguments.get("include_source_link", True))
    activate = bool(arguments.get("activate", True))
    description = arguments.get("description")

    workflow = _build_wordpress_workflow(
        name=name,
        webhook_path=webhook_path,
        wordpress_url=wordpress_url,
        credential_id=credential_id,
        status=status,
        categories=categories,
        include_source_link=include_source_link,
        activate=activate,
        description=description,
    )

    webhook_urls = n8n_client.build_webhook_urls(webhook_path)
    api_result: Optional[Dict[str, Any]] = None

    if n8n_client.api_ready():
        api_result = await n8n_client.create_workflow(workflow)
    else:
        logger.warning("n8n API not configured; returning workflow JSON for manual import")

    return {
        "status": api_result.get("status") if api_result else "pending_api_config",
        "workflow": workflow,
        "webhook_urls": webhook_urls,
        "api_result": api_result,
    }




# ============================================================================
# Remote n8n MCP client — proxy to external n8n MCP server (added 2026-06-04)
# Restored from auto-stash backup (stash@{2})
# ============================================================================

DEFAULT_N8N_MCP_URL = "https://n8n.ailinux.me/mcp-server/http"

N8N_MCP_TOOL_SCHEMA: Dict[str, Any] = {
    "name": "n8n_mcp_call",
    "description": (
        "Call the configured remote n8n MCP server via streamable HTTP/SSE. "
        "Use method like tools/list, search_workflows, get_workflow_details, "
        "validate_workflow, or create_workflow_from_code."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "description": "Remote MCP JSON-RPC method, e.g. tools/list, search_workflows",
            },
            "params": {
                "type": "object",
                "description": "Remote MCP params object",
                "additionalProperties": True,
            },
            "id": {"type": ["string", "integer"], "description": "Optional JSON-RPC id"},
            "timeout": {"type": "number", "description": "Request timeout in seconds", "default": 60},
        },
        "required": ["method"],
        "additionalProperties": False,
    },
}


def _extract_sse_json(text: str) -> Dict[str, Any]:
    """Extract the first JSON object from a text/event-stream response."""
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        parsed = _stdlib_json.loads(data)
        if not isinstance(parsed, dict):
            raise ValueError("Remote n8n MCP data event is not a JSON object")
        return parsed

    stripped = text.strip()
    if stripped.startswith("{"):
        parsed = _stdlib_json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("Remote n8n MCP returned no JSON data event")


async def handle_n8n_mcp_call(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Proxy a JSON-RPC call to the configured n8n MCP server."""
    method = arguments.get("method")
    if not method or not isinstance(method, str):
        raise ValueError("'method' parameter is required")

    remote_params = arguments.get("params") or {}
    if not isinstance(remote_params, dict):
        raise ValueError("'params' must be an object when provided")

    url = os.environ.get("N8N_MCP_URL", DEFAULT_N8N_MCP_URL).strip()
    token = os.environ.get("N8N_MCP_TOKEN", "").strip()
    if not token:
        raise ValueError("N8N_MCP_TOKEN is not configured in the TriForce environment")

    payload = {
        "jsonrpc": "2.0",
        "id": arguments.get("id", 1),
        "method": method,
        "params": remote_params,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    async with httpx.AsyncClient(timeout=float(arguments.get("timeout", 60))) as client:
        response = await client.post(url, json=payload, headers=headers)

    if response.status_code >= 400:
        raise ValueError(f"n8n MCP HTTP {response.status_code}: {response.text[:500]}")

    data = _extract_sse_json(response.text)
    if "error" in data:
        raise ValueError(f"n8n MCP error: {data['error']}")

    return {
        "remote": "n8n",
        "url": url,
        "method": method,
        "response": data,
        "result": data.get("result"),
    }


N8N_TOOLS = [
    {
        "name": "n8n.workflow.create",
        "description": "Create a webhook-to-WordPress workflow in n8n (webhook → HTTP Request → Respond). Returns webhook URLs and workflow JSON.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Workflow name"},
                "webhook_path": {"type": "string", "description": "Path after /webhook/ (auto-slugged if omitted)"},
                "wordpress_url": {"type": "string", "description": "WordPress base URL or full posts endpoint"},
                "credential_id": {"type": "string", "description": "n8n credential ID for WordPress basic auth"},
                "status": {"type": "string", "enum": ["publish", "draft", "private"], "description": "Post status"},
                "categories": {"type": "array", "items": {"type": "integer"}, "description": "Category IDs"},
                "include_source_link": {"type": "boolean", "description": "Append <Quelle> link from source_url"},
                "activate": {"type": "boolean", "description": "Activate workflow immediately"},
                "description": {"type": "string", "description": "Sticky note text stored in workflow"},
            },
        },
    },
    N8N_MCP_TOOL_SCHEMA,
]

N8N_HANDLERS = {
    "n8n.workflow.create": handle_n8n_workflow_create,
    "n8n_mcp_call": handle_n8n_mcp_call,
}
