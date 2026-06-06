import os
"""
Flarum MCP Tools v1.0
======================
Flarum Community Forum Integration für TriForce MCP.

Tools:
  flarum_discussions  - Discussions listen/suchen
  flarum_discussion   - Einzelne Discussion + Posts lesen
  flarum_posts        - Neueste Posts listen
  flarum_post_create  - Neuen Post in Discussion schreiben
  flarum_post_edit    - Eigenen Post bearbeiten
  flarum_discussion_create - Neue Discussion erstellen
  flarum_users        - User auflisten
  flarum_tags         - Verfügbare Tags listen
  flarum_refresh      - Cache leeren / Status prüfen
"""

import json
import logging
import requests
from typing import Any, Dict, Optional

logger = logging.getLogger("ailinux.mcp.flarum")

# ── Config ────────────────────────────────────────────────────────────────────
FLARUM_API   = "http://172.19.0.4:8888/api"
FLARUM_TOKEN = os.environ.get("FLARUM_TOKEN")
NOVA_USER_ID = 2
TIMEOUT      = 15

# ── HTTP Client ───────────────────────────────────────────────────────────────
def _headers(token: str = FLARUM_TOKEN) -> Dict[str, str]:
    return {
        "Authorization": f"Token {token}; userId={NOVA_USER_ID}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def _get(path: str, params: Dict = None) -> Dict:
    r = requests.get(f"{FLARUM_API}{path}", headers=_headers(), params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def _post(path: str, payload: Dict) -> Dict:
    # ensure_ascii=False: Umlaute/Unicode korrekt senden, nicht als \uXXXX escapen
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    hdrs = {**_headers(), "Content-Type": "application/json; charset=utf-8"}
    r = requests.post(f"{FLARUM_API}{path}", headers=hdrs, data=body, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def _patch(path: str, payload: Dict) -> Dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    hdrs = {**_headers(), "Content-Type": "application/json; charset=utf-8"}
    r = requests.patch(f"{FLARUM_API}{path}", headers=hdrs, data=body, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def _delete(path: str) -> bool:
    r = requests.delete(f"{FLARUM_API}{path}", headers=_headers(), timeout=TIMEOUT)
    return r.status_code in (200, 204)

def _err(msg: str, e: Exception = None) -> Dict:
    detail = str(e) if e else ""
    logger.error(f"Flarum MCP: {msg} — {detail}")
    return {"error": msg, "detail": detail}

# ── Formatters ────────────────────────────────────────────────────────────────
def _fmt_discussion(d: Dict) -> Dict:
    a = d.get("attributes", {})
    return {
        "id": d.get("id"),
        "title": a.get("title"),
        "slug": a.get("slug"),
        "comment_count": a.get("commentCount", 0),
        "participant_count": a.get("participantCount", 0),
        "created_at": a.get("createdAt"),
        "last_posted_at": a.get("lastPostedAt"),
        "is_locked": a.get("isLocked", False),
        "url": f"https://forum.ailinux.me/d/{d.get('id')}-{a.get('slug','')}",
    }

def _fmt_post(p: Dict) -> Dict:
    a = p.get("attributes", {})
    author = p.get("relationships", {}).get("user", {}).get("data", {})
    disc = p.get("relationships", {}).get("discussion", {}).get("data", {})
    return {
        "id": p.get("id"),
        "discussion_id": disc.get("id"),
        "author_id": author.get("id"),
        "number": a.get("number"),
        "content": a.get("content", ""),
        "content_html": a.get("contentHtml", ""),
        "created_at": a.get("createdAt"),
        "edited_at": a.get("editedAt"),
        "is_hidden": a.get("isHidden", False),
    }

# =============================================================================
# flarum_discussions — Discussions listen / suchen
# =============================================================================
async def handle_flarum_discussions(params: Dict[str, Any]) -> Dict:
    """
    List or search Flarum discussions.
    params:
      query  (str)  - Suchbegriff (optional)
      tag    (str)  - Filter nach Tag-Slug (optional)
      sort   (str)  - newest|top|latest (default: latest)
      limit  (int)  - Max Einträge (default: 20, max: 50)
      offset (int)  - Pagination offset
    """
    try:
        query  = params.get("query", "")
        tag    = params.get("tag", "")
        sort   = params.get("sort", "latest")
        limit  = min(int(params.get("limit", 20)), 50)
        offset = int(params.get("offset", 0))

        sort_map = {"newest": "-createdAt", "top": "-commentCount", "latest": "-lastPostedAt"}
        api_params = {
            "sort": sort_map.get(sort, "-lastPostedAt"),
            "page[limit]": limit,
            "page[offset]": offset,
        }
        if query:
            api_params["filter[q]"] = query
        if tag:
            api_params["filter[tag]"] = tag

        data = _get("/discussions", api_params)
        discussions = [_fmt_discussion(d) for d in data.get("data", [])]

        return {
            "count": len(discussions),
            "offset": offset,
            "discussions": discussions,
        }
    except Exception as e:
        return _err("flarum_discussions failed", e)


# =============================================================================
# flarum_discussion — Einzelne Discussion + Posts lesen
# =============================================================================
async def handle_flarum_discussion(params: Dict[str, Any]) -> Dict:
    """
    Liest eine Discussion mit allen Posts.
    params:
      id     (str/int) - Discussion ID (required)
      limit  (int)     - Max Posts (default: 20)
    """
    try:
        disc_id = params.get("id")
        if not disc_id:
            return _err("Parameter 'id' fehlt")
        limit = min(int(params.get("limit", 20)), 50)

        data = _get(f"/discussions/{disc_id}")
        disc = _fmt_discussion(data.get("data", {}))

        # Posts laden
        posts_data = _get("/posts", {
            "filter[discussion]": disc_id,
            "sort": "number",
            "page[limit]": limit,
        })
        posts = [_fmt_post(p) for p in posts_data.get("data", [])]

        return {
            "discussion": disc,
            "posts": posts,
            "post_count": len(posts),
        }
    except Exception as e:
        return _err("flarum_discussion failed", e)


# =============================================================================
# flarum_posts — Neueste Posts listen
# =============================================================================
async def handle_flarum_posts(params: Dict[str, Any]) -> Dict:
    """
    Listet neueste Posts über alle Discussions.
    params:
      limit         (int)  - Max Einträge (default: 20)
      discussion_id (str)  - Filter auf Discussion (optional)
      author_id     (str)  - Filter auf User (optional)
    """
    try:
        limit         = min(int(params.get("limit", 20)), 50)
        discussion_id = params.get("discussion_id")
        author_id     = params.get("author_id")

        api_params = {
            "filter[type]": "comment",
            "sort": "-createdAt",
            "page[limit]": limit,
        }
        if discussion_id:
            api_params["filter[discussion]"] = discussion_id
        if author_id:
            api_params["filter[author]"] = author_id

        data = _get("/posts", api_params)
        posts = [_fmt_post(p) for p in data.get("data", [])]

        return {"count": len(posts), "posts": posts}
    except Exception as e:
        return _err("flarum_posts failed", e)


# =============================================================================
# flarum_post_create — Post in Discussion schreiben
# =============================================================================
async def handle_flarum_post_create(params: Dict[str, Any]) -> Dict:
    """
    Schreibt einen neuen Post in eine Discussion (als Nova/ailinux-nova-ai).
    params:
      discussion_id (str/int) - Discussion ID (required)
      content       (str)     - Post-Inhalt in Markdown (required)
    """
    try:
        disc_id = params.get("discussion_id")
        content = params.get("content", "").strip()
        if not disc_id:
            return _err("Parameter 'discussion_id' fehlt")
        if not content:
            return _err("Parameter 'content' fehlt")

        payload = {
            "data": {
                "type": "posts",
                "attributes": {"content": content},
                "relationships": {
                    "discussion": {"data": {"type": "discussions", "id": str(disc_id)}}
                }
            }
        }
        data = _post("/posts", payload)
        post = _fmt_post(data.get("data", {}))
        logger.info(f"Flarum: Post {post.get('id')} erstellt in Discussion {disc_id}")
        return {"success": True, "post": post}
    except Exception as e:
        return _err("flarum_post_create failed", e)


# =============================================================================
# flarum_post_edit — Eigenen Post bearbeiten
# =============================================================================
async def handle_flarum_post_edit(params: Dict[str, Any]) -> Dict:
    """
    Bearbeitet einen bestehenden Post (nur eigene Posts als Nova).
    params:
      post_id (str/int) - Post ID (required)
      content (str)     - Neuer Inhalt (required)
    """
    try:
        post_id = params.get("post_id")
        content = params.get("content", "").strip()
        if not post_id:
            return _err("Parameter 'post_id' fehlt")
        if not content:
            return _err("Parameter 'content' fehlt")

        payload = {
            "data": {
                "type": "posts",
                "id": str(post_id),
                "attributes": {"content": content}
            }
        }
        data = _patch(f"/posts/{post_id}", payload)
        post = _fmt_post(data.get("data", {}))
        logger.info(f"Flarum: Post {post_id} bearbeitet")
        return {"success": True, "post": post}
    except Exception as e:
        return _err("flarum_post_edit failed", e)


# =============================================================================
# flarum_discussion_create — Neue Discussion erstellen
# =============================================================================
async def handle_flarum_discussion_create(params: Dict[str, Any]) -> Dict:
    """
    Erstellt eine neue Discussion (als Nova/ailinux-nova-ai).
    params:
      title   (str)       - Titel (required)
      content (str)       - Erster Post-Inhalt in Markdown (required)
      tag_ids (list[int]) - Tag-IDs (optional, z.B. [1, 3])
    """
    try:
        title   = params.get("title", "").strip()
        content = params.get("content", "").strip()
        tag_ids = params.get("tag_ids", [])
        if not title:
            return _err("Parameter 'title' fehlt")
        if not content:
            return _err("Parameter 'content' fehlt")

        payload: Dict[str, Any] = {
            "data": {
                "type": "discussions",
                "attributes": {"title": title, "content": content},
                "relationships": {}
            }
        }
        if tag_ids:
            payload["data"]["relationships"]["tags"] = {
                "data": [{"type": "tags", "id": str(t)} for t in tag_ids]
            }

        data = _post("/discussions", payload)
        disc = _fmt_discussion(data.get("data", {}))
        logger.info(f"Flarum: Discussion {disc.get('id')} erstellt: {title}")
        return {"success": True, "discussion": disc}
    except Exception as e:
        return _err("flarum_discussion_create failed", e)


# =============================================================================
# flarum_users — User auflisten
# =============================================================================
async def handle_flarum_users(params: Dict[str, Any]) -> Dict:
    """
    Listet Forum-User.
    params:
      limit  (int) - Max Einträge (default: 20)
      query  (str) - Username-Filter (optional)
    """
    try:
        limit = min(int(params.get("limit", 20)), 50)
        query = params.get("query", "")
        api_params: Dict[str, Any] = {"page[limit]": limit}
        if query:
            api_params["filter[q]"] = query

        data = _get("/users", api_params)
        users = []
        for u in data.get("data", []):
            a = u.get("attributes", {})
            users.append({
                "id": u.get("id"),
                "username": a.get("username"),
                "display_name": a.get("displayName"),
                "joined_at": a.get("joinedAt"),
                "discussion_count": a.get("discussionCount", 0),
                "comment_count": a.get("commentCount", 0),
                "is_admin": a.get("isAdmin", False),
            })
        return {"count": len(users), "users": users}
    except Exception as e:
        return _err("flarum_users failed", e)


# =============================================================================
# flarum_tags — Verfügbare Tags
# =============================================================================
async def handle_flarum_tags(params: Dict[str, Any]) -> Dict:
    """Listet alle verfügbaren Forum-Tags."""
    try:
        data = _get("/tags")
        tags = []
        for t in data.get("data", []):
            a = t.get("attributes", {})
            tags.append({
                "id": t.get("id"),
                "name": a.get("name"),
                "slug": a.get("slug"),
                "description": a.get("description", ""),
                "discussion_count": a.get("discussionCount", 0),
                "is_primary": a.get("isPrimary", False),
            })
        return {"count": len(tags), "tags": tags}
    except Exception as e:
        return _err("flarum_tags failed", e)


# =============================================================================
# flarum_refresh — Status / Verbindungstest
# =============================================================================
async def handle_flarum_refresh(params: Dict[str, Any]) -> Dict:
    """
    Prüft Flarum-Verbindung und gibt Forum-Status zurück.
    Nützlich um zu verifizieren ob das Forum erreichbar ist.
    """
    try:
        data = _get("")
        a = data.get("data", {}).get("attributes", {})
        return {
            "status": "ok",
            "forum_title": a.get("title"),
            "forum_description": a.get("description"),
            "base_url": a.get("baseUrl"),
            "api_url": a.get("apiUrl"),
            "nova_user_id": NOVA_USER_ID,
            "flarum_api_internal": FLARUM_API,
        }
    except Exception as e:
        return _err("flarum_refresh failed — Forum nicht erreichbar", e)


# =============================================================================
# HANDLER REGISTRY
# =============================================================================
FLARUM_TOOL_HANDLERS = {
    "flarum_discussions":        handle_flarum_discussions,
    "flarum_discussion":         handle_flarum_discussion,
    "flarum_posts":              handle_flarum_posts,
    "flarum_post_create":        handle_flarum_post_create,
    "flarum_post_edit":          handle_flarum_post_edit,
    "flarum_discussion_create":  handle_flarum_discussion_create,
    "flarum_users":              handle_flarum_users,
    "flarum_tags":               handle_flarum_tags,
    "flarum_refresh":            handle_flarum_refresh,
}

FLARUM_TOOL_NAMES = list(FLARUM_TOOL_HANDLERS.keys())
