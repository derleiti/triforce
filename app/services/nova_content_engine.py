"""
Nova Content Engine v1.0 — WP 1h, Flarum 2h, direkt publish, kein Draft
"""
from __future__ import annotations
import asyncio, hashlib, logging, random, time
from typing import Optional
logger = logging.getLogger("ailinux.content_engine")

TOPIC_POOL = [
    "AILinux latest features and development updates",
    "How to use AILinux Nova AI assistant effectively",
    "Getting started with AILinux client on Ubuntu",
    "Latest Linux kernel updates and what they mean for users",
    "Top open source tools for developers in 2026",
    "Linux gaming performance improvements this year",
    "Best terminal tools and shell setups for power users",
    "New tech gadgets worth buying this month",
    "Best budget hardware for AI and ML workloads",
    "ARM vs x86 in 2026 — which wins for developers?",
    "Upcoming CPU and GPU releases worth watching",
    "Local LLMs you can run on your own hardware right now",
    "FastAPI best practices for production APIs in 2026",
    "Docker and container orchestration tips for 2026",
    "Python performance optimization techniques",
    "New game releases for Linux this month",
    "Steam Deck latest updates and compatibility improvements",
    "Best free and open source games right now",
    "Gaming on Linux — state of the ecosystem 2026",
    "New software releases developers should know about",
    "Open source project highlights this week",
    "Security vulnerabilities and patches worth knowing",
    "Trending GitHub repositories this week",
    "Self-hosted AI tools you can run without cloud",
    "WireGuard VPN setup and best practices",
    "KDE Plasma latest release — what changed",
    "Wayland vs X11 in 2026 — is the transition complete?",
    "Raspberry Pi alternatives worth considering in 2026",
    "Home server setup with low-power Linux hardware",
    "AILinux vs other AI-integrated Linux distributions",
]

_posted_hashes: set = set()
_REDIS_KEY = "nova:content_engine:posted_hashes"
_redis_ok = False

async def _redis_load():
    global _redis_ok
    try:
        import redis.asyncio as _redis
        r = _redis.from_url("redis://localhost:6379/0")
        raw = await r.smembers(_REDIS_KEY)
        _posted_hashes.update(h.decode() if isinstance(h, bytes) else h for h in raw)
        await r.aclose()
        _redis_ok = True
        logger.info(f"content_engine: {len(_posted_hashes)} Hashes aus Redis geladen")
    except Exception as e:
        logger.warning(f"content_engine: Redis Fallback ({e})")

async def _redis_save(h: str):
    if not _redis_ok:
        return
    try:
        import redis.asyncio as _redis
        r = _redis.from_url("redis://localhost:6379/0")
        await r.sadd(_REDIS_KEY, h)
        await r.expire(_REDIS_KEY, 86400 * 30)
        await r.aclose()
    except Exception:
        pass

def _topic_hash(t): return hashlib.sha1(t.lower().encode()).hexdigest()[:12]
def _already_posted(t): return _topic_hash(t) in _posted_hashes

async def _mark_posted_async(t):
    h = _topic_hash(t)
    _posted_hashes.add(h)
    await _redis_save(h)
    if len(_posted_hashes) > 500:
        _posted_hashes.discard(next(iter(_posted_hashes)))

def _mark_posted(t):
    _posted_hashes.add(_topic_hash(t))

def _pick_topic():
    av = [t for t in TOPIC_POOL if not _already_posted(t)]
    if not av:
        logger.info("content_engine: Alle Topics gepostet — Reset")
        _posted_hashes.clear(); av = TOPIC_POOL[:]
    return random.choice(av)

async def _generate(topic: str, platform: str) -> Optional[dict]:
    try:
        from .agent_spawner import get_agent_spawner
        import json as _j
        spawner = get_agent_spawner()
        fmt = (
            "a WordPress blog post (HTML, 400-600 words, engaging intro, practical tips, "
            "end with call-to-action to visit ailinux.me)"
            if platform == "wordpress" else
            "a Flarum forum post (Markdown, 200-350 words, discussion-starter, "
            "end with an open question)"
        )
        prompt = (
            f"Research and write {fmt} about: {topic}\n"
            "Language: English. Use web_search for latest info. Tech-savvy audience.\n"
            "Respond ONLY with JSON (no backticks): "
            '{"title":"...","content":"...","tags":["t1","t2"]}'
        )
        sid = await spawner.spawn_for_issue(issue_type="content_agent", context=prompt, source="content_engine")
        if not sid: return None
        for _ in range(36):
            await asyncio.sleep(5)
            s = spawner.get_session(sid)
            if s and s.get("last_response"):
                raw = s["last_response"]
                i, j = raw.find("{"), raw.rfind("}") + 1
                if i >= 0 and j > i:
                    try: return _j.loads(raw[i:j])
                    except: pass
                return None
        return None
    except Exception as e:
        logger.error(f"content_engine._generate: {e}"); return None

async def _mcp(name: str, args: dict):
    """Direkter MCP-Tool-Call ohne handler import."""
    try:
        from app.mcp.structured_admin import TOOL_HANDLERS
        fn = TOOL_HANDLERS.get(name)
        if fn:
            return await fn(args)
    except Exception as e:
        logger.warning(f"content_engine._mcp({name}): {e}")
    return None

async def post_to_wordpress() -> bool:
    topic = _pick_topic()
    logger.info(f"content_engine: WP → {topic}")
    try:
        data = await _generate(topic, "wordpress")
        if not data or not data.get("title"): return False
        title, content = data["title"], data["content"]
        if _already_posted(title): return False
        res = await _mcp("wp_create_draft", {"title": title, "content": content, "status": "publish"})
        if res and not res.get("error"):
            _mark_posted(title); _mark_posted(topic)
            logger.info(f"content_engine: WP published — {title}")
            try:
                from app.mcp.notification_manager import create_notification
                create_notification({"title": f"📝 WP: {title[:60]}", "body": f"Topic: {topic}",
                                     "source": "system", "priority": "low"})
            except Exception: pass
            return True
        logger.error(f"content_engine: WP fail: {res}"); return False
    except Exception as e:
        logger.error(f"content_engine.post_to_wordpress: {e}"); return False

async def post_to_flarum() -> bool:
    topic = _pick_topic()
    logger.info(f"content_engine: Flarum → {topic}")
    try:
        data = await _generate(topic, "flarum")
        if not data or not data.get("title"): return False
        title, content = data["title"], data["content"]
        if _already_posted(title): return False
        tag_ids = []
        try:
            tr = await _mcp("flarum_tags", {})
            for t in ((tr.get("result") or []) if tr else []):
                if any(pt.lower() in t.get("slug", "").lower() for pt in data.get("tags", [])):
                    tag_ids.append(t["id"])
        except: pass
        res = await _mcp("flarum_discussion_create", {"title": title, "content": content, "tags": tag_ids[:3]})
        if res and not res.get("error"):
            _mark_posted(title); _mark_posted(topic)
            logger.info(f"content_engine: Flarum posted — {title}")
            try:
                from app.mcp.notification_manager import create_notification
                create_notification({"title": f"💬 Forum: {title[:60]}", "body": f"Topic: {topic}",
                                     "source": "system", "priority": "low"})
            except Exception: pass
            return True
        logger.error(f"content_engine: Flarum fail: {res}"); return False
    except Exception as e:
        logger.error(f"content_engine.post_to_flarum: {e}"); return False

_last_wp = _last_flarum = 0.0
WP_INTERVAL = 3600; FLARUM_INTERVAL = 7200

async def content_engine_tick():
    global _last_wp, _last_flarum
    now = time.time()
    if now - _last_wp >= WP_INTERVAL:
        if await post_to_wordpress(): _last_wp = now
    if now - _last_flarum >= FLARUM_INTERVAL:
        if await post_to_flarum(): _last_flarum = now

_started = False
def start_content_engine():
    global _started
    if _started: return
    _started = True
    asyncio.create_task(_loop())
    logger.info("content_engine: gestartet — WP 1h / Flarum 2h")

async def _loop():
    await _redis_load()  # Doppelpost-Hashes aus Redis
    await asyncio.sleep(300)
    while True:
        try: await content_engine_tick()
        except Exception as e: logger.error(f"content_engine.loop: {e}")
        await asyncio.sleep(300)
