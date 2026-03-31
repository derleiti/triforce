"""
HiveMind v1.0 — Semantische Textkomprimierung mit Kontexterhaltung
===================================================================
Langer Agent-Output → Ollama (qwen3:8b lokal) → Kernaussagen destilliert
~75% Token-Reduktion. Original in Redis (hive_recall abrufbar).

API:
    result = await compress(text, context_key=None, model="qwen3:8b")
    original = await recall(context_key)
    stats = await get_stats()
"""
from __future__ import annotations
import asyncio
import hashlib
import json
import logging
import time
from typing import Optional

logger = logging.getLogger("ailinux.hivemind")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OLLAMA_URL      = "http://localhost:11434/api/generate"
DEFAULT_MODEL   = "qwen3.5:cloud"   # via Ollama Cloud-Proxy
REDIS_PREFIX    = "hive:"
REDIS_TTL       = 86400 * 7   # 7 Tage
MIN_INPUT_CHARS = 500          # Texte kürzer als das nicht komprimieren

COMPRESS_PROMPT = """\
Du bist ein Textverdichter. Deine Aufgabe: Extrahiere alle wesentlichen \
Informationen aus dem folgenden Text und gib sie als kompakte Zusammenfassung aus.

REGELN:
- Behalte ALLE konkreten Fakten: Dateinamen, Zeilennummern, Fehlermeldungen, \
Commit-Hashes, IPs, Status-Codes, Timestamps
- Behalte alle Handlungsempfehlungen und offenen TODOs
- Entferne: Wiederholungen, Füllwörter, Meta-Kommentare, Höflichkeitsformeln
- Ausgabe: Fließtext oder nummerierte Liste — was kürzer ist
- Keine Einleitung, kein Abschluss, direkt zum Inhalt
- Ziel: ~25% der Originallänge

TEXT:
{text}

KOMPRIMIERTER OUTPUT:"""


# ---------------------------------------------------------------------------
# Redis helper
# ---------------------------------------------------------------------------
def _get_redis():
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
        return r
    except Exception as e:
        logger.debug(f"hivemind: Redis nicht verfügbar: {e}")
        return None


# ---------------------------------------------------------------------------
# Ollama call (async, streaming=False)
# ---------------------------------------------------------------------------
async def _ollama_generate(text: str, model: str) -> Optional[str]:
    import aiohttp
    prompt = COMPRESS_PROMPT.format(text=text[:12000])  # hard cap
    payload = {
        "model":  model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 2048},
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OLLAMA_URL, json=payload, timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"hivemind: Ollama HTTP {resp.status}")
                    return None
                data = await resp.json()
                return data.get("response", "").strip() or None
    except Exception as e:
        logger.warning(f"hivemind: Ollama-Fehler: {e}")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def compress(
    text:        str,
    context_key: Optional[str] = None,
    model:       str = DEFAULT_MODEL,
) -> dict:
    """
    Komprimiert `text` via Ollama.
    Returns:
        {
            "compressed": str,       # komprimierter Text
            "original_chars": int,
            "compressed_chars": int,
            "ratio": float,          # compression ratio (0..1, kleiner = besser)
            "context_key": str,      # Redis-Key für hive_recall
            "stored": bool,          # True wenn Original in Redis
        }
    Falls Komprimierung fehlschlägt oder Text zu kurz → original zurück.
    """
    if len(text) < MIN_INPUT_CHARS:
        return {
            "compressed": text,
            "original_chars": len(text),
            "compressed_chars": len(text),
            "ratio": 1.0,
            "context_key": None,
            "stored": False,
            "skipped": True,
        }

    t0 = time.time()
    compressed = await _ollama_generate(text, model)

    if not compressed or len(compressed) >= len(text):
        logger.debug("hivemind: Komprimierung ergab keinen Gewinn, Original beibehalten")
        return {
            "compressed": text,
            "original_chars": len(text),
            "compressed_chars": len(text),
            "ratio": 1.0,
            "context_key": None,
            "stored": False,
            "fallback": True,
        }

    # Key erzeugen
    if not context_key:
        context_key = REDIS_PREFIX + hashlib.sha256(text[:500].encode()).hexdigest()[:16]
    elif not context_key.startswith(REDIS_PREFIX):
        context_key = REDIS_PREFIX + context_key

    # Original in Redis speichern
    stored = False
    r = _get_redis()
    if r:
        try:
            r.setex(context_key, REDIS_TTL, text)
            stored = True
        except Exception as e:
            logger.warning(f"hivemind: Redis-Store fehlgeschlagen: {e}")

    ratio = len(compressed) / len(text)
    elapsed = round(time.time() - t0, 1)
    logger.info(
        f"hivemind: {len(text)} → {len(compressed)} chars "
        f"({ratio:.0%} ratio) in {elapsed}s | key={context_key}"
    )

    return {
        "compressed":       compressed,
        "original_chars":   len(text),
        "compressed_chars": len(compressed),
        "ratio":            round(ratio, 3),
        "context_key":      context_key,
        "stored":           stored,
        "elapsed_s":        elapsed,
    }


async def recall(context_key: str) -> Optional[str]:
    """Holt den Original-Text aus Redis."""
    if not context_key.startswith(REDIS_PREFIX):
        context_key = REDIS_PREFIX + context_key
    r = _get_redis()
    if not r:
        return None
    try:
        return r.get(context_key)
    except Exception as e:
        logger.warning(f"hivemind: recall fehlgeschlagen: {e}")
        return None


async def get_stats() -> dict:
    """Gibt Redis-Stats über gespeicherte Originals zurück."""
    r = _get_redis()
    if not r:
        return {"available": False}
    try:
        keys = r.keys(f"{REDIS_PREFIX}*")
        total_bytes = sum(
            r.memory_usage(k) or 0 for k in keys[:50]
        )
        return {
            "available":    True,
            "stored_count": len(keys),
            "total_bytes":  total_bytes,
            "model":        DEFAULT_MODEL,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


# ---------------------------------------------------------------------------
# MCP Tool Handler (wird in mcp_handlers registriert)
# ---------------------------------------------------------------------------

async def mcp_hivemind_compress(args: dict) -> dict:
    text        = args.get("text", "")
    context_key = args.get("context_key")
    model       = args.get("model", DEFAULT_MODEL)
    if not text:
        return {"error": "text erforderlich"}
    return await compress(text, context_key=context_key, model=model)


async def mcp_hivemind_recall(args: dict) -> dict:
    context_key = args.get("context_key", "")
    if not context_key:
        return {"error": "context_key erforderlich"}
    original = await recall(context_key)
    if original is None:
        return {"error": f"Key nicht gefunden oder abgelaufen: {context_key}"}
    return {"original": original, "chars": len(original)}


async def mcp_hivemind_stats(args: dict) -> dict:
    return await get_stats()

