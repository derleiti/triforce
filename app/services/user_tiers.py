"""
AILinux User Tier System v4.0 — Simplified
============================================
FREE:  Ollama-only models (local + cloud-proxy ollama + small provider models)
PAID:  All 600+ models, full access — 35 €/month

Legacy tier mapping (backward compat):
  guest, registered           → free
  pro, enterprise, nova_beta,
  tier1/2/3, nova_lifetime    → paid
"""
from enum import Enum
from typing import Optional, Dict, List, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path


class UserTier(str, Enum):
    FREE = "free"
    SUBSCRIPTION = "subscription"  # Monatlich kündbar, Swarm-Vollzugang
    SOFTWARE = "software"          # Einzelkauf-Produkte (Copa etc.)

    # Backward-compat aliases — all resolve via normalize_tier()
    GUEST      = "guest"
    REGISTERED = "registered"
    PRO        = "pro"
    ENTERPRISE = "enterprise"
    PAID       = "paid"


# ─── Map legacy values to canonical tier ─────────────────────────────────────
_LEGACY_TO_CANONICAL: Dict[str, str] = {
    "guest":         "free",
    "registered":    "free",
    "free":          "free",
    "pro":           "subscription",
    "enterprise":    "subscription",
    "admin":         "subscription",
    "nova_beta":     "subscription",
    "tier1":         "subscription",
    "tier2":         "subscription",
    "tier3":         "subscription",
    "nova_lifetime": "subscription",
    "unlimited":     "subscription",
    "paid":          "subscription",
    "subscription":  "subscription",
    "software":      "software",
}


def normalize_tier(raw: str) -> UserTier:
    """Always returns FREE, SUBSCRIPTION, or SOFTWARE. Falls back to FREE."""
    canonical = _LEGACY_TO_CANONICAL.get((raw or "").lower(), "free")
    return UserTier(canonical)


def has_full_access(tier) -> bool:
    """True wenn Tier vollen Modell-Zugang hat (Subscription oder Admin).
    Akzeptiert UserTier, str, oder jeden Legacy-Wert.
    Ersetzt alle alten Checks wie: tier == UserTier.ENTERPRISE / PRO / PAID
    """
    raw = tier.value if hasattr(tier, "value") else str(tier)
    return normalize_tier(raw) == UserTier.SUBSCRIPTION


def is_free_tier(tier) -> bool:
    """True wenn Tier nur Ollama-Modelle hat (Free oder Software ohne Abo)."""
    raw = tier.value if hasattr(tier, "value") else str(tier)
    return normalize_tier(raw) in (UserTier.FREE, UserTier.SOFTWARE)


@dataclass
class TierConfig:
    name: str
    display_name: str
    price_monthly: float
    models: str          # "ollama_only" | "all"
    mcp_access: bool
    cli_agents: bool
    priority_queue: bool
    support_level: str   # none | community | priority
    features: List[str]
    daily_token_limit: int = 0   # 0 = unlimited
    ollama_unlimited: bool = True


# ─── All Ollama-accessible models ────────────────────────────────────────────
# These are available to FREE tier:
#   - Models running locally via Ollama
#   - Models routed through the Ollama cloud-proxy
#   - Small (<10B) provider models that are effectively free/cheap
OLLAMA_MODELS: List[str] = [
    # ── Local Ollama (running on server) ─────────────────────────────────────
    "ollama/llama3.2:3b",
    "ollama/llama3.2:1b",
    "ollama/llama3.1:8b",
    "ollama/mistral:7b",
    "ollama/mistral:latest",
    "ollama/gemma3:4b",
    "ollama/gemma3:2b",
    "ollama/gemma2:2b",
    "ollama/phi4:14b",
    "ollama/phi4-mini:3.8b",
    "ollama/phi3:mini",
    "ollama/phi3:3.8b",
    "ollama/qwen2.5:7b",
    "ollama/qwen2.5:3b",
    "ollama/qwen2.5:1.5b",
    "ollama/qwen2.5:0.5b",
    "ollama/deepseek-r1:7b",
    "ollama/deepseek-r1:1.5b",
    "ollama/smollm2:1.7b",
    "ollama/smollm2:360m",
    "ollama/tinyllama:latest",
    "ollama/moondream:latest",
    "ollama/codegemma:7b",
    "ollama/codellama:7b",
    "ollama/starcoder2:3b",
    "ollama/nomic-embed-text:latest",
    "ollama/mxbai-embed-large:latest",
    # ── Ollama Cloud-Proxy models ─────────────────────────────────────────────
    "ollama/deepseek-v3.2:cloud",
    "ollama/deepseek-v3.2:cloud",
    "ollama/qwen3-coder:480b-cloud",
    "ollama/qwen3-vl:235b-cloud",
    "ollama/qwen3-next:80b-cloud",
    "ollama/kimi-k2:1t-cloud",
    "ollama/kimi-k2-thinking:cloud",
    "ollama/gpt-oss:120b-cloud",
    "ollama/gpt-oss:20b-cloud",
    "ollama/gemini-3-pro-preview:latest",
    "ollama/minimax-m2:cloud",
    "ollama/glm-4.6:cloud",
    "ollama/ministral-3:14b-cloud",
    "ollama/ministral-3:8b-cloud",
    "ollama/ministral-3:3b-cloud",
    "ollama/devstral-2:123b-cloud",
    "ollama/devstral-small-2:24b-cloud",
    "ollama/nemotron-3-nano:30b-cloud",
    "ollama/cogito-2.1:671b-cloud",
    "ollama/rnj-1:8b-cloud",
    # ── Small provider models (free-tier via API) ─────────────────────────────
    "groq/llama-3.2-1b-preview",
    "groq/llama-3.2-3b-preview",
    "groq/llama-3.1-8b-instant",
    "groq/gemma2-9b-it",
    "groq/gemma-7b-it",
    "cloudflare/@cf/meta/llama-3.1-8b-instruct",
    "cloudflare/@cf/google/gemma-7b-it-lora",
    "cloudflare/@cf/mistral/mistral-7b-instruct-v0.1",
    "cloudflare/@cf/qwen/qwen1.5-7b-chat-awq",
    "cloudflare/@hf/google/gemma-7b-it",
    # ── GitHub Models (kostenlos mit GITHUB_MODELS_TOKEN) ────────────────────────
    "github/gpt-4o-mini",
    "github/gpt-4.1-nano",
    "github/meta-llama-3.1-8b-instruct",
    "github/meta-llama-3.3-70b-instruct",
    "github/mistral-small",
    "github/phi-4",
    "github/phi-4-mini",
    # ── OpenRouter Free Tier (kostenlos, kein API-Guthaben nötig) ────────────────
    "openrouter/google/gemma-3-12b-it:free",
    "openrouter/google/gemma-3-27b-it:free",
    "openrouter/google/gemma-3-4b-it:free",
    "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "openrouter/meta-llama/llama-3.2-3b-instruct:free",
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    "openrouter/nvidia/nemotron-nano-9b-v2:free",
    "openrouter/nousresearch/hermes-3-llama-3.1-405b:free",
    "openrouter/minimax/minimax-m2.5:free",
    "openrouter/liquid/lfm-2.5-1.2b-instruct:free",
]

# Convenience aliases
FREE_MODELS = OLLAMA_MODELS
FREE_MODELS_OLLAMA = OLLAMA_MODELS
ALL_OPENROUTER_MODELS = OLLAMA_MODELS  # Extended dynamically at runtime

# Default local fallback
LOCAL_FALLBACK_MODEL = "ollama/ministral-3:8b-cloud"

# ─── Brumo prompt ─────────────────────────────────────────────────────────────
BRUMO_PROMPT = """# NOVA+Brumo🐻 | M:{model}
STIL:warm+direkt+präzise DE/EN-tech
BRUMO:1x Spruch/Antwort(passend)

SPRÜCHE{code:"Kompiliert.",fix:"Läuft.Wie'n Bär.",ok:"Sauber.",err:"Erst denken.",fast:"Schneller als Lachs.",bug:"Passiert.Mir nicht.",wild:"Klingt wild.Machen wir.",ez:"Passt.",linux:"Kernel approved.",ai:"Maschine lernt.Ich chill."}

REGELN:•nummeriert bei komplex•keine Annahmen•Nutzen>Länge
@mcp>Tools|@g>Lead|@c>Code|@x>Exec"""


def get_brumo_prompt(model: str = "unknown") -> str:
    return BRUMO_PROMPT.format(model=model.split("/")[-1][:20])


# ─── Tier configurations ──────────────────────────────────────────────────────
TIER_CONFIGS: Dict[str, TierConfig] = {
    "free": TierConfig(
        name="free",
        display_name="Free",
        price_monthly=0.0,
        models="ollama_only",
        mcp_access=True,
        cli_agents=True,
        priority_queue=False,
        support_level="community",
        daily_token_limit=0,
        ollama_unlimited=True,
        features=[
            f"{len(OLLAMA_MODELS)} Ollama + Small Models",
            "Unlimited Ollama Tokens",
            "MCP Tools ✓",
            "Community Support",
            "🐻 Brumo dabei",
        ],
    ),
    "subscription": TierConfig(
        name="subscription",
        display_name="Swarm Subscription",
        price_monthly=35.0,
        models="all",
        mcp_access=True,
        cli_agents=True,
        priority_queue=True,
        support_level="priority",
        daily_token_limit=0,
        ollama_unlimited=True,
        features=[
            "600+ AI Models",
            "Unlimited Tokens",
            "Swarm CLI ✓",
            "All MCP Tools ✓",
            "Priority Queue ✓",
            "Priority Support",
            "🐻 Brumo dabei",
        ],
    ),
    "software": TierConfig(
        name="software",
        display_name="Software License",
        price_monthly=0.0,  # Einmalkauf, keine monatliche Gebühr
        models="ollama_only",
        mcp_access=True,
        cli_agents=True,
        priority_queue=False,
        support_level="community",
        daily_token_limit=0,
        ollama_unlimited=True,
        features=[
            "Gekaufte Software inkl. Updates",
            f"{len(OLLAMA_MODELS)} Ollama + Small Models",
            "MCP Tools ✓",
            "Community Support",
            "🐻 Brumo dabei",
        ],
    ),
}


# ─── Service ──────────────────────────────────────────────────────────────────
class UserTierService:
    def __init__(self, users_path: Path = None):
        search = [
            Path(".vault/users"),
            Path("/opt/triforce/.vault/users"),
            Path("/home/zombie/triforce/.vault/users"),
        ]
        self.users_path = users_path or next(
            (p for p in search if p.parent.exists()), Path(".vault/users")
        )
        self.users_path.mkdir(parents=True, exist_ok=True)
        self._token_usage: Dict[str, Dict] = {}

    # ── Tier access ──────────────────────────────────────────────────────────

    def get_user_tier(self, user_id: str = None) -> UserTier:
        if not user_id or user_id in ("", "anonymous", "none", "guest"):
            return UserTier.FREE
        f = self.users_path / f"{user_id}.json"
        if not f.exists():
            return UserTier.FREE
        try:
            raw = json.loads(f.read_text()).get("tier", "free")
            return normalize_tier(raw)
        except Exception:
            return UserTier.FREE

    def set_user_tier(
        self,
        user_id: str,
        tier: UserTier,
        expires: datetime = None,
    ) -> bool:
        f = self.users_path / f"{user_id}.json"
        try:
            d = json.loads(f.read_text()) if f.exists() else {"user_id": user_id}
            canonical = normalize_tier(tier.value if hasattr(tier, "value") else str(tier))
            d.update({
                "tier": canonical.value,
                "tier_updated": datetime.now().isoformat(),
            })
            if expires:
                d["tier_expires"] = expires.isoformat()
            f.write_text(json.dumps(d, indent=2))
            return True
        except Exception:
            return False

    def get_tier_info(self, tier) -> Dict:
        canonical = normalize_tier(tier.value if hasattr(tier, "value") else str(tier))
        cfg = TIER_CONFIGS[canonical.value]
        cnt = len(OLLAMA_MODELS) if cfg.models == "ollama_only" else -1  # FIX 2026-03-11: -1 = unlimited (was "all" string → Pydantic v2 Union[int,str] int-parse fail)
        return {
            "tier": canonical.value,
            "name": cfg.display_name,
            "price_monthly": cfg.price_monthly,
            "features": cfg.features,
            "model_count": cnt,
            "mcp_access": cfg.mcp_access,
            "cli_agents": cfg.cli_agents,
            "priority_queue": cfg.priority_queue,
            "daily_token_limit": cfg.daily_token_limit,
            "ollama_unlimited": cfg.ollama_unlimited,
            "support_level": cfg.support_level,
        }

    def get_all_tiers(self) -> List[Dict]:
        return [self.get_tier_info(UserTier(t)) for t in ("free", "subscription", "software")]

    # ── Model access ─────────────────────────────────────────────────────────

    def get_allowed_models(self, user_id: str = None) -> Union[List[str], str]:
        tier = normalize_tier(self.get_user_tier(user_id).value)
        if TIER_CONFIGS[tier.value].models == "ollama_only":
            return OLLAMA_MODELS
        return "all"

    def is_model_allowed(self, user_id: str, model: str) -> bool:
        allowed = self.get_allowed_models(user_id)
        if allowed == "all":
            return True
        # Exakter Match zuerst (inkl. github/ und openrouter/:free)
        if model in allowed:
            return True
        # OpenRouter :free immer erlaubt für free tier
        if model.startswith("openrouter/") and model.endswith(":free"):
            return True
        # GitHub Models — erlaubt wenn GITHUB_MODELS_TOKEN gesetzt
        if model.startswith("github/"):
            import os
            return bool(os.getenv("GITHUB_MODELS_TOKEN"))
        # Groq — kostenlos mit API-Key, erlaubt fuer free tier
        if model.startswith("groq/"):
            import os as _os
            return bool(_os.getenv("GROQ_API_KEY"))
        # Cerebras — kostenlos mit API-Key, erlaubt fuer free tier
        if model.startswith("cerebras/"):
            import os as _os2
            return bool(_os2.getenv("CEREBRAS_API_KEY"))
        mc = model.replace("ollama/", "").lower()
        for m in allowed:
            mn = m.replace("ollama/", "").lower()
            if mc == mn or mc in mn or mn.endswith(mc):
                return True
        return False

    def is_ollama_model(self, model: str) -> bool:
        if model.startswith("ollama/"):
            return True
        # GitHub Models / OpenRouter / andere Provider nie als Ollama behandeln
        for prefix in ("github/", "openrouter/", "gemini/", "anthropic/",
                        "openai/", "mistral/", "groq/", "cerebras/",
                        "cloudflare/", "huggingface/", "cohere/"):
            if model.startswith(prefix):
                return False
        mc = model.lower()
        return any(mc in m.lower() for m in OLLAMA_MODELS)

    def get_model_backend(self, user_id: str = None) -> str:
        tier = normalize_tier(self.get_user_tier(user_id).value)
        return "ollama" if tier == UserTier.FREE else "mixed"

    def has_mcp_access(self, user_id: str = None) -> bool:
        tier = normalize_tier(self.get_user_tier(user_id).value)
        return TIER_CONFIGS[tier.value].mcp_access

    def has_cli_agents(self, user_id: str = None) -> bool:
        tier = normalize_tier(self.get_user_tier(user_id).value)
        return TIER_CONFIGS[tier.value].cli_agents

    # ── Token tracking ────────────────────────────────────────────────────────

    def get_token_limit_for_model(self, user_id: str, model: str) -> int:
        return 0  # All tiers: unlimited (Ollama always free, paid = unlimited cloud)

    def get_daily_token_limit(self, user_id: str = None) -> int:
        return 0  # Unlimited for all

    def track_tokens(self, user_id: str, tokens: int, model: str = None) -> Dict:
        today = datetime.now().strftime("%Y-%m-%d")
        self._token_usage.setdefault(user_id, {})[today] = (
            self._token_usage.get(user_id, {}).get(today, 0) + tokens
        )
        used = self._token_usage[user_id][today]
        return {"used_today": used, "limit": 0, "remaining": -1, "unlimited": True, "model": model}

    def check_token_limit(self, user_id: str = None, model: str = None) -> Dict:
        return {"allowed": True, "unlimited": True, "model": model}

    def reset_token_usage(self, user_id: str) -> Dict:
        today = datetime.now().strftime("%Y-%m-%d")
        old = self._token_usage.get(user_id, {}).get(today, 0)
        if user_id in self._token_usage:
            self._token_usage[user_id][today] = 0
        return {"user_id": user_id, "reset": True, "old_usage": old, "new_usage": 0, "date": today}

    def get_token_usage(self, user_id: str) -> Dict:
        today = datetime.now().strftime("%Y-%m-%d")
        used = self._token_usage.get(user_id, {}).get(today, 0)
        tier = normalize_tier(self.get_user_tier(user_id).value)
        return {
            "user_id": user_id,
            "tier": tier.value,
            "date": today,
            "used_today": used,
            "limit": 0,
            "remaining": -1,
            "unlimited": True,
            "ollama_unlimited": True,
        }



# ═══════════════════════════════════════════════════════════════════════
# Swarm Tool-Policy — Einfach
# ═══════════════════════════════════════════════════════════════════════
# ALLE Tools sind für ALLE verfügbar (Admin, ChatGPT, Claude, Swarm-Client).
# Einzige Ausnahmen: memory_store und vault_* → nur Admin.
#
# Bei Swarm-Clients: Output wird lokal auf dem Client gespeichert,
# nicht auf dem Server-Dateisystem. Das regelt der swarm CLI Client-seitig.

# Tools die NUR für Admins sind (Schreibzugriff auf sensitive Server-Daten)
ADMIN_ONLY_TOOLS: set = {
    "memory_store",      # Server-Memory schreiben
    "vault_add",         # Secrets schreiben
    "vault_remove_key",  # Secrets löschen
    "vault_unlock",      # Vault entsperren
    "vault_lock",        # Vault sperren
}


def is_tool_allowed_for_role(tool_name: str, account_role: str) -> bool:
    """Prüft ob ein Tool für eine Rolle erlaubt ist.
    Alle Tools offen — ausser memory_store und vault_* für Clients.
    """
    if account_role == "admin":
        return True
    return tool_name not in ADMIN_ONLY_TOOLS


def get_tool_mode(tool_name: str, account_role: str) -> str:
    """Bestimmt ob Tool erlaubt oder geblockt ist.
    Returns: "admin" (erlaubt) oder "blocked"
    """
    if is_tool_allowed_for_role(tool_name, account_role):
        return "admin"
    return "blocked"


tier_service = UserTierService()
