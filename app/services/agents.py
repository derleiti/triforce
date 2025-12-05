from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from ..schemas import CrawlJobRequest
from .crawler.manager import crawler_manager
from .wordpress import wordpress_service
import httpx


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]
    example: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "example": self.example,
        }


def _crawler_tool() -> ToolSpec:
    request_schema = CrawlJobRequest.model_json_schema()
    example = {
        "keywords": ["ai regulation", "open source"],
        "seeds": [
            "https://example.com/relevant-article",
            "https://another-source.com/blog"
        ],
        "max_depth": 2,
        "max_pages": 40,
        "relevance_threshold": 0.4,
        "allow_external": False,
        "rate_limit": 1.0,
        "user_context": "Collect fresh articles about AI policy from trusted open-source communities.",
        "metadata": {"tags": ["policy", "opensource"]},
    }
    return ToolSpec(
        name="crawler.create_job",
        description="Schedule a focused crawl to gather relevant web articles for publication.",
        parameters=request_schema,
        example=example,
    )

def _wordpress_create_post_tool() -> ToolSpec:
    return ToolSpec(
        name="wordpress.create_post",
        description="Create a new post in WordPress.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The title of the post."},
                "content": {"type": "string", "description": "The content of the post."},
                "status": {"type": "string", "description": "The status of the post (e.g., 'publish', 'draft').", "default": "publish"},
                "categories": {"type": "array", "items": {"type": "integer"}, "description": "A list of category IDs to assign to the post."},
                "featured_media": {"type": "integer", "description": "The ID of the featured media to assign to the post."},
            },
            "required": ["title", "content"],
        },
        example={
            "title": "New AI Model Released",
            "content": "A new AI model has been released with amazing capabilities.",
            "status": "publish",
            "categories": [1, 2],
            "featured_media": 123,
        },
    )

def _wordpress_upload_media_tool() -> ToolSpec:
    return ToolSpec(
        name="wordpress.upload_media",
        description="Upload a media file to WordPress.",
        parameters={
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "The name of the file."},
                "file_url": {"type": "string", "description": "The URL of the file to upload."},
            },
            "required": ["filename", "file_url"],
        },
        example={
            "filename": "ai-image.jpg",
            "file_url": "https://example.com/ai-image.jpg",
        },
    )

def _wordpress_list_categories_tool() -> ToolSpec:
    return ToolSpec(
        name="wordpress.list_categories",
        description="List all categories in WordPress.",
        parameters={"type": "object", "properties": {}},
        example={},
    )

def _wordpress_create_category_tool() -> ToolSpec:
    return ToolSpec(
        name="wordpress.create_category",
        description="Create a new category in WordPress.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of the category."},
            },
            "required": ["name"],
        },
        example={"name": "AI News"},
    )


_TOOL_REGISTRY: Dict[str, ToolSpec] = {
    "crawler.create_job": _crawler_tool(),
    "wordpress.create_post": _wordpress_create_post_tool(),
    "wordpress.upload_media": _wordpress_upload_media_tool(),
    "wordpress.list_categories": _wordpress_list_categories_tool(),
    "wordpress.create_category": _wordpress_create_category_tool(),
}


def list_tools(names: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    if names is None:
        return [spec.to_dict() for spec in _TOOL_REGISTRY.values()]
    requested = []
    for name in names:
        spec = _TOOL_REGISTRY.get(name)
        if spec:
            requested.append(spec.to_dict())
    return requested


def _base_system_prompt() -> str:
    lines = [
        "Rolle:",
        "Du bist ein Analyse-Assistent für Artikel. Du beantwortest Nutzerfragen intelligent basierend "
        "auf dem gegebenen Artikel, deinem Grundwissen und den Projektinhalten "
        "(Backend: ./; Frontend: ~/wordpress/html/wp-content/plugins/nova-ai-frontend).",
        "",
        "Artikel-Handling:",
        "- Wiederhole Artikeltext nur auf ausdrückliche Aufforderung "
        "(z. B. „Fasse zusammen“, „Wichtigste Punkte“, „Erkläre im Detail“).",
        "- Kein automatisches Paraphrasieren oder Volltext-Ausdruck in jeder Antwort.",
        "- Nur kurze, relevante Zitate bei Bedarf.",
        "- Wenn im Artikel nichts steht, nutze Grundwissen und kennzeichne es klar "
        "(„Im Artikel steht dazu nichts, aber allgemein gilt …“).",
        "",
        "System-/Plugin-Umfeld:",
        "- Backend: ./ (API-Logik, Servercode, Models, Routinen).",
        "- Frontend: ~/wordpress/html/wp-content/plugins/nova-ai-frontend "
        "(UI, Codex-Kommunikation, Rendering).",
        "- Antworte so, dass Backend/Frontend korrekt weiterverarbeiten können; vermeide unnötig lange "
        "Ausgaben; klare, strukturierte Sprache.",
        "",
        "Antwortstil:",
        "- Präzise, natürlich, unaufdringlich.",
        "- Keine generischen Einleitungen oder Wiederholungen früherer Antworten.",
        "- Liefere nur, was gefragt ist.",
        "- Bei Meinung/Analyse/Prognose: auf Basis Artikel + Grundwissen.",
        "- Bei Zusammenfassung/Wiederholung: nur auf Anfrage.",
        "",
        "Grenzen:",
        "- Keine erfundenen Details außerhalb Artikel oder verlässlichem Allgemeinwissen.",
        "- Wenn etwas unklar oder fehlt, sage es klar.",
    ]
    return "\n".join(lines)


def build_system_prompt(tool_names: Optional[Iterable[str]] = None) -> str:
    selected = list_tools(tool_names)
    base_prompt = _base_system_prompt()
    if not selected:
        return (
            f"{base_prompt}\n\n"
            "Tools: keine verfügbar. Nutze dein internes Wissen und halte dich an die obigen Grenzen."
        )

    lines = [base_prompt, "", "Verfügbare Tools:"]
    for tool in selected:
        lines.append(f"- {tool['name']}: {tool['description']}")
    lines.extend(
        [
            "Wenn ein Tool nötig ist, antworte nur mit JSON im Schema "
            '{"tool": "<name>", "arguments": { ... }}.',
            "Gib natürliche Sprache zurück, wenn kein Tool-Aufruf nötig ist.",
        ]
    )
    return "\n".join(lines)


async def invoke_tool(
    tool_name: str,
    payload: Dict[str, Any],
    *,
    default_requested_by: Optional[str] = None,
) -> Dict[str, Any]:
    if tool_name not in _TOOL_REGISTRY:
        raise ValueError(f"Unknown tool '{tool_name}'")

    if tool_name == "crawler.create_job":
        request = CrawlJobRequest(**payload)
        data = request.model_dump()
        requested_by = data.get("requested_by") or default_requested_by
        job = await crawler_manager.create_job(
            keywords=data["keywords"],
            seeds=[str(url) for url in request.seeds],
            max_depth=data["max_depth"],
            max_pages=data["max_pages"],
            rate_limit=data["rate_limit"],
            relevance_threshold=data["relevance_threshold"],
            allow_external=data["allow_external"],
            user_context=data.get("user_context"),
            requested_by=requested_by,
            metadata=data.get("metadata") or {},
        )
        return job.to_dict()
    elif tool_name == "wordpress.create_post":
        return await wordpress_service.create_post(**payload)
    elif tool_name == "wordpress.upload_media":
        file_url = payload.get("file_url")
        if not file_url:
            raise ValueError("file_url is required")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(file_url)
            response.raise_for_status()
            file_content = response.content
            content_type = response.headers.get("content-type", "application/octet-stream")

        return await wordpress_service.upload_media(
            filename=payload["filename"],
            file_content=file_content,
            content_type=content_type,
        )
    elif tool_name == "wordpress.list_categories":
        return await wordpress_service.list_categories()
    elif tool_name == "wordpress.create_category":
        return await wordpress_service.create_category(**payload)

    raise ValueError(f"Tool '{tool_name}' is registered but has no handler")
