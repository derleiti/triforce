"""
app/utils/redaction.py
=======================
Zentrale Redaction-Utility für externe MCP-Antworten.

Default-Deny: Wenn ein Schlüsselname nach Secret aussieht
(KEY/TOKEN/PASSWORD/SECRET/JWT/COOKIE/SESSION/CREDENTIAL/AUTH),
wird der Wert NIE im Klartext zurückgegeben. Externe Aufrufer
sehen entweder einen "<redacted>"-Marker oder einen reinen
"_configured": bool-Status.

Public API:
- is_secret_key(name) -> bool
- redact_value(key, value, mode="redact"|"presence") -> Any
- redact_dict(data, mode=...) -> Dict
- safe_provider_status(providers, source) -> Dict[provider, {api_key_configured, base_url_configured}]
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

# Secret-Pattern (Default-Deny). Keys werden lower-case verglichen.
_SECRET_TOKENS: Tuple[str, ...] = (
    "key",
    "token",
    "password",
    "passwd",
    "pass",
    "secret",
    "credential",
    "credentials",
    "auth",
    "authorization",
    "cookie",
    "session",
    "jwt",
    "private",
    "psk",
    "salt",
    "signature",
    "bearer",
    "api_key",
)

# Allowlist: enthält "key"/"auth"/"session" im Namen, ist aber harmlos.
_NON_SECRET_ALLOWLIST: Tuple[str, ...] = (
    "key_source",
    "key_count",
    "keys_count",
    "public_key_id",
    "key_type",
    "key_id",
    "auth_method",
    "auth_type",
    "auth_enabled",
    "auth_required",
    "session_count",
    "session_id_prefix",
)

REDACTED_MARKER = "<redacted>"


def is_secret_key(name: str) -> bool:
    """True, wenn der Schlüssel nach Secret aussieht (Default-Deny).

    Tokens werden mit Wortgrenzen geprüft (Underscore/Hyphen/CamelCase/Anfang/Ende),
    damit z.B. ``MAIL_SMTP_PASS`` matcht (Token ``pass``) ohne ``compass``
    oder ``passing`` als Secret zu klassifizieren.
    """
    if not name:
        return False
    lower = name.lower()
    if lower in _NON_SECRET_ALLOWLIST:
        return False
    # CamelCase nur bei gemischtem Case anwenden — sonst zerhackt es ALLCAPS-Namen.
    if any(c.isupper() for c in name) and any(c.islower() for c in name):
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    else:
        snake = lower
    parts = re.split(r"[_\-\.\s]+", snake)
    for part in parts:
        if part in _SECRET_TOKENS:
            return True
    # Fallback: substring-Match nur fuer die laengeren, eindeutigen Tokens
    for tok in ("password", "passwd", "secret", "credential", "credentials",
                "authorization", "api_key", "private_key"):
        if tok in lower:
            return True
    return False


def _looks_like_secret_value(value: Any) -> bool:
    """Heuristik: lange opake Strings (>=24 Zeichen, base64/hex-ish) sind verdächtig."""
    if not isinstance(value, str):
        return False
    if len(value) < 24:
        return False
    if re.fullmatch(r"[A-Za-z0-9+/=_\-]{24,}", value):
        return True
    if value.startswith(("sk-", "sk_", "pk_", "Bearer ", "ghp_", "gho_", "ghs_")):
        return True
    return False


def redact_value(key: str, value: Any, *, mode: str = "redact") -> Any:
    """
    Redact einen einzelnen Wert.

    mode="redact"   -> Secret-Werte werden zu "<redacted>".
    mode="presence" -> Secret-Werte werden zu bool (True wenn gesetzt).
    """
    if is_secret_key(key) or _looks_like_secret_value(value):
        if mode == "presence":
            return bool(value) if value is not None else False
        return REDACTED_MARKER
    return value


def redact_dict(data: Mapping[str, Any], *, mode: str = "redact") -> Dict[str, Any]:
    """
    Redact ein flaches oder geschachteltes Dict.
    """
    if not isinstance(data, Mapping):
        return {}
    out: Dict[str, Any] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            continue
        if is_secret_key(key):
            if value is None:
                out[key] = False if mode == "presence" else None
            else:
                out[key] = bool(value) if mode == "presence" else REDACTED_MARKER
            continue
        if isinstance(value, Mapping):
            out[key] = redact_dict(value, mode=mode)
        elif isinstance(value, list):
            new_list = []
            for v in value:
                if isinstance(v, Mapping):
                    new_list.append(redact_dict(v, mode=mode))
                elif isinstance(v, str) and _looks_like_secret_value(v):
                    new_list.append(REDACTED_MARKER if mode == "redact" else True)
                else:
                    new_list.append(v)
            out[key] = new_list
        else:
            if _looks_like_secret_value(value):
                out[key] = REDACTED_MARKER if mode == "redact" else True
            else:
                out[key] = value
    return out


def safe_provider_status(
    providers: Iterable[str],
    *,
    source: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Dict[str, bool]]:
    """
    Gibt für jeden angefragten Provider nur Bool-Status zurück.
    Nie echte Werte, nie Präfixe, nie Dateipfade.

    Format pro Provider:
      {
        "api_key_configured": bool,
        "base_url_configured": bool,
      }

    `source` kann eine Mapping (z.B. dict aus settings) sein. Default: os.environ.
    """
    src: Mapping[str, Any] = source if source is not None else os.environ

    def _has(*candidates: str) -> bool:
        for cand in candidates:
            val = src.get(cand) if hasattr(src, "get") else None
            if val:
                return True
        return False

    result: Dict[str, Dict[str, bool]] = {}
    for raw in providers:
        if not isinstance(raw, str):
            continue
        name = raw.strip().lower()
        if not name:
            continue

        key_candidates: List[str] = []
        url_candidates: List[str] = []

        if name in ("hive", "hyve"):
            key_candidates = ["HIVE_API_KEY", "HYVE_API_KEY"]
            url_candidates = ["HIVE_BASE_URL", "HYVE_BASE_URL"]
        elif name == "openai":
            key_candidates = ["OPENAI_API_KEY"]
            url_candidates = ["OPENAI_BASE_URL"]
        elif name == "anthropic":
            key_candidates = ["ANTHROPIC_API_KEY"]
        elif name == "groq":
            key_candidates = ["GROQ_API_KEY"]
            url_candidates = ["GROQ_BASE_URL"]
        elif name == "mistral":
            key_candidates = ["MISTRAL_API_KEY"]
        elif name == "gemini":
            key_candidates = ["GEMINI_API_KEY"]
        elif name == "cerebras":
            key_candidates = ["CEREBRAS_API_KEY"]
            url_candidates = ["CEREBRAS_BASE_URL"]
        elif name == "openrouter":
            key_candidates = ["OPENROUTER_API_KEY"]
            url_candidates = ["OPENROUTER_BASE_URL"]
        elif name == "huggingface":
            key_candidates = ["HUGGINGFACE_API_KEY", "HF_API_KEY"]
            url_candidates = ["HUGGINGFACE_INFERENCE_URL"]
        elif name == "github":
            key_candidates = ["GITHUB_TOKEN"]
            url_candidates = ["GITHUB_MODELS_BASE_URL"]
        elif name == "cohere":
            key_candidates = ["COHERE_API_KEY"]
        elif name == "together":
            key_candidates = ["TOGETHER_API_KEY"]
            url_candidates = ["TOGETHER_BASE_URL"]
        elif name == "fireworks":
            key_candidates = ["FIREWORKS_API_KEY"]
            url_candidates = ["FIREWORKS_BASE_URL"]
        elif name == "cloudflare":
            key_candidates = ["CLOUDFLARE_API_TOKEN"]
        elif name == "jina":
            key_candidates = ["JINA_API_KEY"]
        elif name == "ollama":
            key_candidates = ["OLLAMA_BEARER_TOKEN"]
            url_candidates = ["OLLAMA_BASE", "OLLAMA_BASE_URL"]
        else:
            key_candidates = [f"{name.upper()}_API_KEY", f"{name.upper()}_KEY"]
            url_candidates = [f"{name.upper()}_BASE_URL", f"{name.upper()}_URL"]

        result[name] = {
            "api_key_configured": _has(*key_candidates),
            "base_url_configured": _has(*url_candidates),
        }

    return result


__all__ = [
    "REDACTED_MARKER",
    "is_secret_key",
    "redact_value",
    "redact_dict",
    "safe_provider_status",
]
