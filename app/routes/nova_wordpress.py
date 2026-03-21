"""
WordPress MCP Routes — TriForce Backend
WP-CLI-basierte Verwaltung via Docker exec (wordpress_fpm Container)
Posts, Pages, Media, Users, Settings, Stats
"""
import logging
import subprocess
import json
import re
from fastapi import Depends, Header, APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any

import os as _os_wp

def _require_wp_admin(x_internal_key: str = Header(default="")):
    expected = _os_wp.environ.get("INTERNAL_API_KEY", "")
    if not expected or x_internal_key != expected:
        raise HTTPException(status_code=403, detail="Forbidden")

router = APIRouter(prefix="/v1/wordpress", tags=["wordpress"])
logger = logging.getLogger("ailinux.wordpress.routes")

WP_CONTAINER = "wordpress_fpm"
WP_PATH = "/var/www/html"
WP_CLI = f"wp --allow-root --path={WP_PATH}"


# ─── Helper ───────────────────────────────────────────────────────────────────

def wp(cmd: str, json_output: bool = True) -> Any:
    """WP-CLI im wordpress_fpm Container ausführen."""
    fmt = " --format=json" if json_output else ""
    full_cmd = f"docker exec {WP_CONTAINER} {WP_CLI} {cmd}{fmt}"
    try:
        result = subprocess.run(
            full_cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip()
        # WP-CLI gibt Notices auf stdout — filtern
        lines = [l for l in output.splitlines()
                 if not l.startswith("Notice:") and not l.startswith("Warning:")
                 and "sendmail" not in l and "textdomain" not in l.lower()]
        clean = "\n".join(lines).strip()

        if json_output and clean:
            try:
                return json.loads(clean)
            except json.JSONDecodeError:
                return {"raw": clean}
        return clean
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="WP-CLI timeout")
    except Exception as e:
        logger.error("WP helper command failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


def wp_raw(cmd: str) -> str:
    return wp(cmd, json_output=False)


# ─── Models ───────────────────────────────────────────────────────────────────

class PostCreate(BaseModel):
    title: str
    content: str
    status: str = "draft"  # draft | publish | private
    post_type: str = "post"  # post | page
    categories: Optional[str] = None   # kommagetrennte Namen
    tags: Optional[str] = None
    excerpt: Optional[str] = None
    author: int = 1

class PostUpdate(BaseModel):
    post_id: int
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    excerpt: Optional[str] = None

class PageCreate(BaseModel):
    title: str
    content: str
    status: str = "draft"
    parent: Optional[int] = None
    template: Optional[str] = None
    author: int = 1

class EmailSettings(BaseModel):
    admin_email: str
    blogname: Optional[str] = None
    mailpoet_sender_name: Optional[str] = None
    mailpoet_sender_email: Optional[str] = None


# ─── Posts ────────────────────────────────────────────────────────────────────

@router.get("/posts")
def list_posts(status: str = "any", limit: int = 20, post_type: str = "post"):
    """Posts auflisten."""
    valid_status = {"publish", "draft", "private", "any", "trash", "pending"}
    if status not in valid_status:
        raise HTTPException(400, f"Ungültiger Status: {status}")
    data = wp(f"post list --post_type={post_type} --post_status={status} "
              f"--posts_per_page={limit} --fields=ID,post_title,post_status,post_date,post_type")
    return {"ok": True, "posts": data if isinstance(data, list) else []}


@router.post("/posts")
def create_post(body: PostCreate, _auth: None = Depends(_require_wp_admin)):
    """Neuen Post oder Page erstellen."""
    # Titel + Content escapen
    title = body.title.replace('"', '\\"')
    content = body.content.replace('"', '\\"').replace('\n', '\\n')

    cmd_parts = [
        f'post create --post_title="{title}"',
        f'--post_content="{content}"',
        f'--post_status={body.status}',
        f'--post_type={body.post_type}',
        f'--post_author={body.author}',
        '--porcelain',
    ]
    if body.excerpt:
        cmd_parts.append(f'--post_excerpt="{body.excerpt.replace(chr(34), chr(92)+chr(34))}"')

    result = wp_raw(" ".join(cmd_parts))

    # porcelain gibt nur die Post-ID zurück
    post_id = None
    for line in result.splitlines():
        line = line.strip()
        if line.isdigit():
            post_id = int(line)
            break

    if not post_id:
        logger.error("WP post creation returned no post_id. Raw result: %s", result)
        raise HTTPException(500, "Post konnte nicht erstellt werden")

    # Tags + Kategorien nachträglich setzen
    if body.categories:
        wp_raw(f'post term set {post_id} category {body.categories.replace(",", " ")}')
    if body.tags:
        wp_raw(f'post term set {post_id} post_tag {body.tags.replace(",", " ")}')

    return {"ok": True, "post_id": post_id, "status": body.status, "type": body.post_type}


@router.put("/posts/{post_id}")
def update_post(post_id: int, body: PostUpdate, _auth: None = Depends(_require_wp_admin)):
    """Post aktualisieren."""
    cmd_parts = [f"post update {post_id}"]
    if body.title:
        cmd_parts.append(f'--post_title="{body.title.replace(chr(34), chr(92)+chr(34))}"')
    if body.content:
        cmd_parts.append(f'--post_content="{body.content.replace(chr(34), chr(92)+chr(34)).replace(chr(10), chr(92)+chr(110))}"')
    if body.status:
        cmd_parts.append(f'--post_status={body.status}')
    if body.excerpt:
        cmd_parts.append(f'--post_excerpt="{body.excerpt}"')

    result = wp_raw(" ".join(cmd_parts))
    ok = "Success" in result or "Updated" in result
    return {"ok": ok, "post_id": post_id, "result": result}


@router.delete("/posts/{post_id}")
def delete_post(post_id: int, force: bool = False, _auth: None = Depends(_require_wp_admin)):
    """Post löschen (Trash oder force-delete)."""
    cmd = f"post delete {post_id}" + (" --force" if force else "")
    result = wp_raw(cmd)
    return {"ok": True, "post_id": post_id, "result": result}


@router.post("/posts/{post_id}/publish")
def publish_post(post_id: int, _auth: None = Depends(_require_wp_admin)):
    """Post direkt veröffentlichen."""
    result = wp_raw(f"post update {post_id} --post_status=publish")
    ok = "Success" in result or "Updated" in result
    url_data = wp(f"post get {post_id} --fields=guid")
    url = url_data.get("guid", "") if isinstance(url_data, dict) else ""
    return {"ok": ok, "post_id": post_id, "url": url}


@router.get("/posts/{post_id}")
def get_post(post_id: int):
    """Einzelnen Post abrufen."""
    data = wp(f"post get {post_id} --fields=ID,post_title,post_content,post_status,post_date,post_type,post_author,guid")
    if not data or data == "" or (isinstance(data, dict) and not data.get("ID")):
        raise HTTPException(status_code=404, detail=f"Post {post_id} nicht gefunden")
    return {"ok": True, "post": data}


# ─── Pages ────────────────────────────────────────────────────────────────────

@router.get("/pages")
def list_pages(status: str = "any", limit: int = 50):
    """Alle Seiten auflisten."""
    data = wp(f"post list --post_type=page --post_status={status} "
              f"--posts_per_page={limit} --fields=ID,post_title,post_status,post_date,post_parent")
    return {"ok": True, "pages": data if isinstance(data, list) else []}


@router.post("/pages")
def create_page(body: PageCreate, _auth: None = Depends(_require_wp_admin)):
    """Neue Page erstellen."""
    # Wiederverwendung der Post-Route
    post_body = PostCreate(
        title=body.title,
        content=body.content,
        status=body.status,
        post_type="page",
        author=body.author,
    )
    result = create_post(post_body)
    page_id = result["post_id"]

    if body.parent:
        wp_raw(f"post update {page_id} --post_parent={body.parent}")
    if body.template:
        wp_raw(f"post meta set {page_id} _wp_page_template {body.template}")

    return {"ok": True, "page_id": page_id, "status": body.status}


# ─── Medien ───────────────────────────────────────────────────────────────────

@router.get("/media")
def list_media(limit: int = 20):
    """Medienbibliothek auflisten."""
    data = wp(f"post list --post_type=attachment --posts_per_page={limit} "
              f"--fields=ID,post_title,post_date,guid")
    return {"ok": True, "media": data if isinstance(data, list) else []}


# ─── Kategorien & Tags ────────────────────────────────────────────────────────

@router.get("/categories")
def list_categories():
    """Alle Kategorien."""
    data = wp("term list category --fields=term_id,name,slug,count")
    return {"ok": True, "categories": data if isinstance(data, list) else []}


@router.get("/tags")
def list_tags():
    """Alle Tags."""
    data = wp("term list post_tag --fields=term_id,name,slug,count")
    return {"ok": True, "tags": data if isinstance(data, list) else []}


# ─── Statistiken ──────────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats():
    """WordPress Statistiken."""
    post_count  = wp("post list --post_type=post --post_status=publish --posts_per_page=-1 --fields=ID")
    draft_count = wp("post list --post_type=post --post_status=draft --posts_per_page=-1 --fields=ID")
    page_count  = wp("post list --post_type=page --post_status=publish --posts_per_page=-1 --fields=ID")
    user_count  = wp("user list --fields=ID")
    media_count = wp("post list --post_type=attachment --posts_per_page=-1 --fields=ID")
    blog_url    = wp_raw("option get siteurl")
    blogname    = wp_raw("option get blogname")
    admin_email = wp_raw("option get admin_email")

    return {
        "ok": True,
        "site": {
            "url": blog_url,
            "name": blogname,
            "admin_email": admin_email,
        },
        "counts": {
            "posts_published": len(post_count) if isinstance(post_count, list) else 0,
            "posts_draft": len(draft_count) if isinstance(draft_count, list) else 0,
            "pages": len(page_count) if isinstance(page_count, list) else 0,
            "users": len(user_count) if isinstance(user_count, list) else 0,
            "media": len(media_count) if isinstance(media_count, list) else 0,
        }
    }


# ─── Email / Settings ─────────────────────────────────────────────────────────

@router.get("/settings")
def get_wp_settings():
    """WP-Settings abrufen (Email, Siteurl, Blogname…)."""
    return {
        "ok": True,
        "settings": {
            "admin_email": wp_raw("option get admin_email"),
            "blogname":    wp_raw("option get blogname"),
            "siteurl":     wp_raw("option get siteurl"),
            "home":        wp_raw("option get home"),
            "timezone":    wp_raw("option get timezone_string"),
            "language":    wp_raw("option get WPLANG"),
        }
    }


@router.post("/settings/email")
def update_email_settings(body: EmailSettings):
    """Admin-Email + MailPoet Absender konfigurieren."""
    results = {}

    # WP Admin Email
    r = wp_raw(f'option update admin_email "{body.admin_email}"')
    results["admin_email"] = "updated" if "Success" in r or "unchanged" in r else r

    # WP User 1 Email mitziehen
    r2 = wp_raw(f'user update 1 --user_email="{body.admin_email}"')
    results["user_email"] = "updated" if "Success" in r2 else r2

    # Blogname optional
    if body.blogname:
        r3 = wp_raw(f'option update blogname "{body.blogname}"')
        results["blogname"] = "updated" if "Success" in r3 else r3

    # MailPoet Sender via PHP-Snippet
    if body.mailpoet_sender_email or body.mailpoet_sender_name:
        mp_settings_raw = wp_raw("option get mailpoet_settings --format=json")
        try:
            mp = json.loads(mp_settings_raw)
        except Exception:
            mp = {}
        if "sender" not in mp:
            mp["sender"] = {}
        if body.mailpoet_sender_email:
            mp["sender"]["address"] = body.mailpoet_sender_email
        if body.mailpoet_sender_name:
            mp["sender"]["name"] = body.mailpoet_sender_name
        new_mp = json.dumps(mp).replace('"', '\\"')
        r4 = wp_raw(f'option update mailpoet_settings "{new_mp}"')
        results["mailpoet"] = "updated" if "Success" in r4 else r4

    return {"ok": True, "results": results}


# ─── Users ────────────────────────────────────────────────────────────────────

@router.get("/users")
def list_users():
    """Alle WP-User."""
    data = wp("user list --fields=ID,user_login,user_email,display_name,roles,registered")
    return {"ok": True, "users": data if isinstance(data, list) else []}


# ─── Plugins ──────────────────────────────────────────────────────────────────

@router.get("/plugins")
def list_plugins():
    """Aktive Plugins auflisten."""
    data = wp("plugin list --fields=name,status,version,title")
    return {"ok": True, "plugins": data if isinstance(data, list) else []}


# ─── Suche ────────────────────────────────────────────────────────────────────

@router.get("/search")
def search_posts(q: str, post_type: str = "any", limit: int = 10):
    """Posts/Pages durchsuchen."""
    safe_q = re.sub(r'["\';\\]', '', q)
    data = wp(f'post list --search="{safe_q}" --post_type={post_type} '
              f'--posts_per_page={limit} --fields=ID,post_title,post_status,post_type,post_date')
    return {"ok": True, "results": data if isinstance(data, list) else []}
