"""
Translation Layer: API ↔ MCP Bidirectional Conversion

Provides seamless translation between REST API calls and MCP JSON-RPC calls,
allowing Claude to use either interface interchangeably.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode


@dataclass
class TranslationResult:
    """Result of a translation operation."""
    success: bool
    method: str  # REST endpoint or MCP method
    data: Dict[str, Any]  # Request body or params
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


# =============================================================================
# API to MCP Translation Mappings
# =============================================================================

API_TO_MCP_MAPPINGS = {
    # Chat endpoints
    ("POST", "/v1/chat/completions"): {
        "method": "llm.invoke",
        "transform": lambda body: {
            "model": body.get("model"),
            "messages": body.get("messages", []),
            "options": {
                "temperature": body.get("temperature"),
                "stream": body.get("stream", False),
                "max_tokens": body.get("max_tokens")
            }
        }
    },
    ("POST", "/v1/openai/chat/completions"): {
        "method": "llm.invoke",
        "transform": lambda body: {
            "model": body.get("model"),
            "messages": body.get("messages", []),
            "options": {
                "temperature": body.get("temperature"),
                "stream": body.get("stream", False),
                "max_tokens": body.get("max_tokens")
            }
        }
    },

    # Vision endpoint
    ("POST", "/v1/vision/chat/completions"): {
        "method": "analyze_image",
        "transform": lambda body: {
            "image_url": body.get("image_url") or body.get("image_base64"),
            "prompt": body.get("prompt", "Describe this image"),
            "model": body.get("model", "gemini/gemini-2.0-flash")
        }
    },

    # Models endpoint
    ("GET", "/v1/models"): {
        "method": "list_models",
        "transform": lambda _: {}
    },

    # Crawler endpoints
    ("POST", "/v1/crawler/jobs"): {
        "method": "crawl.site",
        "transform": lambda body: {
            "site_url": body.get("seeds", [""])[0] if body.get("seeds") else "",
            "seeds": body.get("seeds", []),
            "keywords": body.get("keywords", []),
            "max_depth": body.get("max_depth", 2),
            "max_pages": body.get("max_pages", 60),
            "allow_external": body.get("allow_external", False),
            "relevance_threshold": body.get("relevance_threshold", 0.35),
            "priority": body.get("priority", "low"),
            "idempotency_key": body.get("idempotency_key")
        }
    },
    ("GET", "/v1/crawler/jobs/{job_id}"): {
        "method": "crawl.status",
        "transform": lambda body, path_params: {
            "job_id": path_params.get("job_id"),
            "include_results": body.get("include_results", False),
            "include_content": body.get("include_content", False)
        }
    },

    # Posts endpoint
    ("POST", "/v1/posts"): {
        "method": "posts.create",
        "transform": lambda body: {
            "title": body.get("title"),
            "content": body.get("content"),
            "status": body.get("status", "publish"),
            "categories": body.get("categories"),
            "featured_media": body.get("featured_media")
        }
    },

    # Admin endpoints
    ("POST", "/v1/admin/crawler/control"): {
        "method": "admin.crawler.control",
        "transform": lambda body: {
            "action": body.get("action"),
            "instance": body.get("instance")
        }
    },
    ("GET", "/v1/admin/crawler/status"): {
        "method": "admin.crawler.config.get",
        "transform": lambda _: {}
    }
}


# =============================================================================
# MCP to API Translation Mappings
# =============================================================================

MCP_TO_API_MAPPINGS = {
    "llm.invoke": {
        "method": "POST",
        "path": "/v1/chat/completions",
        "transform": lambda params: {
            "model": params.get("model") or params.get("provider_id"),
            "messages": params.get("messages", []),
            "stream": params.get("options", {}).get("stream", False),
            "temperature": params.get("options", {}).get("temperature")
        }
    },

    "list_models": {
        "method": "GET",
        "path": "/v1/models",
        "transform": lambda _: {}
    },

    "analyze_image": {
        "method": "POST",
        "path": "/v1/vision/chat/completions",
        "transform": lambda params: {
            "model": params.get("model", "gemini/gemini-2.0-flash"),
            "prompt": params.get("prompt", "Describe this image"),
            "image_url": params.get("image_url")
        }
    },

    "crawl.url": {
        "method": "POST",
        "path": "/v1/crawler/jobs",
        "transform": lambda params: {
            "seeds": [params.get("url")],
            "keywords": params.get("keywords", []),
            "max_pages": params.get("max_pages", 10),
            "max_depth": 1,
            "priority": "high"  # User crawler is fast
        }
    },

    "crawl.site": {
        "method": "POST",
        "path": "/v1/crawler/jobs",
        "transform": lambda params: {
            "seeds": params.get("seeds") or [params.get("site_url")],
            "keywords": params.get("keywords", []),
            "max_depth": params.get("max_depth", 2),
            "max_pages": params.get("max_pages", 40),
            "allow_external": params.get("allow_external", False),
            "relevance_threshold": params.get("relevance_threshold", 0.35),
            "priority": params.get("priority", "low"),
            "idempotency_key": params.get("idempotency_key")
        }
    },

    "crawl.status": {
        "method": "GET",
        "path": "/v1/crawler/jobs/{job_id}",
        "path_params": ["job_id"],
        "transform": lambda params: {
            "include_results": params.get("include_results", False),
            "include_content": params.get("include_content", False)
        }
    },

    "posts.create": {
        "method": "POST",
        "path": "/v1/posts",
        "transform": lambda params: {
            "title": params.get("title"),
            "content": params.get("content"),
            "status": params.get("status", "publish"),
            "categories": params.get("categories"),
            "featured_media": params.get("featured_media")
        }
    },

    "media.upload": {
        "method": "POST",
        "path": "/v1/media",
        "transform": lambda params: {
            "file_data": params.get("file_data"),
            "filename": params.get("filename"),
            "content_type": params.get("content_type", "application/octet-stream")
        }
    },

    "admin.crawler.control": {
        "method": "POST",
        "path": "/v1/admin/crawler/control",
        "transform": lambda params: {
            "action": params.get("action"),
            "instance": params.get("instance")
        }
    },

    "admin.crawler.config.get": {
        "method": "GET",
        "path": "/v1/admin/crawler/status",
        "transform": lambda _: {}
    },

    "admin.crawler.config.set": {
        "method": "PATCH",
        "path": "/v1/admin/crawler/config",
        "transform": lambda params: {
            k: v for k, v in params.items()
            if k in ["user_crawler_workers", "user_crawler_max_concurrent", "auto_crawler_enabled"]
        }
    }
}


class APIToMCPTranslator:
    """Translates REST API calls to MCP JSON-RPC calls."""

    def __init__(self):
        self.mappings = API_TO_MCP_MAPPINGS

    def translate(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        query_params: Optional[Dict[str, Any]] = None
    ) -> TranslationResult:
        """
        Translate a REST API call to an MCP JSON-RPC call.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., /v1/chat/completions)
            body: Request body
            query_params: Query parameters

        Returns:
            TranslationResult with MCP method and params
        """
        body = body or {}
        query_params = query_params or {}

        # Merge query params into body for GET requests
        if method == "GET":
            body = {**body, **query_params}

        # Try exact match first
        key = (method, path)
        if key in self.mappings:
            mapping = self.mappings[key]
            try:
                params = mapping["transform"](body)
                return TranslationResult(
                    success=True,
                    method=mapping["method"],
                    data=params
                )
            except Exception as e:
                return TranslationResult(
                    success=False,
                    method="",
                    data={},
                    error=f"Transform error: {str(e)}"
                )

        # Try pattern matching for path parameters
        path_params = {}
        for (m, pattern), mapping in self.mappings.items():
            if m != method:
                continue

            # Convert path pattern to regex
            regex_pattern = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', pattern)
            match = re.fullmatch(regex_pattern, path)
            if match:
                path_params = match.groupdict()
                try:
                    # Call transform with path params if it accepts them
                    transform = mapping["transform"]
                    if transform.__code__.co_argcount > 1:
                        params = transform(body, path_params)
                    else:
                        params = transform(body)
                        params.update(path_params)

                    return TranslationResult(
                        success=True,
                        method=mapping["method"],
                        data=params
                    )
                except Exception as e:
                    return TranslationResult(
                        success=False,
                        method="",
                        data={},
                        error=f"Transform error: {str(e)}"
                    )

        return TranslationResult(
            success=False,
            method="",
            data={},
            error=f"No MCP method found for {method} {path}"
        )

    def to_jsonrpc(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        request_id: Union[str, int] = 1
    ) -> Dict[str, Any]:
        """
        Convert REST API call to JSON-RPC request.

        Returns:
            JSON-RPC 2.0 request object
        """
        result = self.translate(method, path, body)
        if not result.success:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": result.error},
                "id": request_id
            }

        return {
            "jsonrpc": "2.0",
            "method": result.method,
            "params": result.data,
            "id": request_id
        }


class MCPToAPITranslator:
    """Translates MCP JSON-RPC calls to REST API calls."""

    def __init__(self, base_url: str = "http://localhost:9100"):
        # Use localhost for internal API calls (no internet required)
        self.base_url = base_url.rstrip("/")
        self.mappings = MCP_TO_API_MAPPINGS

    def translate(
        self,
        mcp_method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> TranslationResult:
        """
        Translate an MCP method call to a REST API call.

        Args:
            mcp_method: MCP method name (e.g., llm.invoke)
            params: MCP method parameters

        Returns:
            TranslationResult with HTTP method, path, and body
        """
        params = params or {}

        if mcp_method not in self.mappings:
            return TranslationResult(
                success=False,
                method="",
                data={},
                error=f"No API endpoint found for MCP method: {mcp_method}"
            )

        mapping = self.mappings[mcp_method]
        http_method = mapping["method"]
        path = mapping["path"]

        # Handle path parameters
        path_params = mapping.get("path_params", [])
        for param_name in path_params:
            if param_name in params:
                path = path.replace(f"{{{param_name}}}", str(params[param_name]))

        try:
            body = mapping["transform"](params)
        except Exception as e:
            return TranslationResult(
                success=False,
                method=http_method,
                data={},
                error=f"Transform error: {str(e)}"
            )

        # For GET requests, convert body to query params
        query_params = {}
        if http_method == "GET" and body:
            query_params = body
            body = {}

        return TranslationResult(
            success=True,
            method=http_method,
            data=body,
            query_params=query_params,
            headers={"Content-Type": "application/json"}
        )

    def to_curl(
        self,
        mcp_method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a curl command for the equivalent REST API call.

        Returns:
            curl command string
        """
        result = self.translate(mcp_method, params)
        if not result.success:
            return f"# Error: {result.error}"

        path = self.mappings[mcp_method]["path"]
        path_params = self.mappings[mcp_method].get("path_params", [])
        for param_name in path_params:
            if params and param_name in params:
                path = path.replace(f"{{{param_name}}}", str(params[param_name]))

        url = f"{self.base_url}{path}"

        if result.query_params:
            url += "?" + urlencode(result.query_params)

        curl_parts = [f"curl -X {result.method}"]

        for key, value in result.headers.items():
            curl_parts.append(f'-H "{key}: {value}"')

        if result.data:
            curl_parts.append(f"-d '{json.dumps(result.data)}'")

        curl_parts.append(f'"{url}"')

        return " \\\n  ".join(curl_parts)

    def to_request_dict(
        self,
        mcp_method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a request dictionary suitable for httpx/requests.

        Returns:
            Dictionary with method, url, headers, json/params keys
        """
        result = self.translate(mcp_method, params)
        if not result.success:
            return {"error": result.error}

        path = self.mappings[mcp_method]["path"]
        path_params = self.mappings[mcp_method].get("path_params", [])
        for param_name in path_params:
            if params and param_name in params:
                path = path.replace(f"{{{param_name}}}", str(params[param_name]))

        request_dict = {
            "method": result.method,
            "url": f"{self.base_url}{path}",
            "headers": result.headers
        }

        if result.method == "GET":
            request_dict["params"] = result.query_params
        else:
            request_dict["json"] = result.data

        return request_dict


class BidirectionalTranslator:
    """
    Unified translator that handles both directions.
    Automatically detects the input format and translates accordingly.
    """

    def __init__(self, base_url: str = "http://localhost:9100"):
        # Use localhost for internal API calls (no internet required)
        self.api_to_mcp = APIToMCPTranslator()
        self.mcp_to_api = MCPToAPITranslator(base_url)

    def translate(self, request: Dict[str, Any]) -> TranslationResult:
        """
        Automatically detect and translate the request.

        If request has 'jsonrpc' key, treat as MCP and translate to API.
        If request has 'method' and 'path' keys, treat as API and translate to MCP.

        Args:
            request: Either a JSON-RPC request or an API request descriptor

        Returns:
            TranslationResult
        """
        if "jsonrpc" in request:
            # MCP to API
            return self.mcp_to_api.translate(
                request.get("method", ""),
                request.get("params", {})
            )
        elif "path" in request:
            # API to MCP
            return self.api_to_mcp.translate(
                request.get("method", "GET"),
                request.get("path", ""),
                request.get("body", {}),
                request.get("query_params", {})
            )
        else:
            return TranslationResult(
                success=False,
                method="",
                data={},
                error="Unknown request format. Expected 'jsonrpc' or 'path' key."
            )

    def translate_and_format(
        self,
        request: Dict[str, Any],
        output_format: str = "auto"
    ) -> Union[Dict[str, Any], str]:
        """
        Translate and format output.

        Args:
            request: Input request
            output_format: 'jsonrpc', 'curl', 'request_dict', or 'auto'

        Returns:
            Formatted output
        """
        if "jsonrpc" in request:
            # MCP → API
            if output_format in ("auto", "curl"):
                return self.mcp_to_api.to_curl(
                    request.get("method", ""),
                    request.get("params", {})
                )
            elif output_format == "request_dict":
                return self.mcp_to_api.to_request_dict(
                    request.get("method", ""),
                    request.get("params", {})
                )
        else:
            # API → MCP
            return self.api_to_mcp.to_jsonrpc(
                request.get("method", "GET"),
                request.get("path", ""),
                request.get("body", {}),
                request.get("id", 1)
            )

        result = self.translate(request)
        return {"success": result.success, "data": result.data, "error": result.error}
