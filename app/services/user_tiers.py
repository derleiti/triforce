"""
AILinux User Tier System v3.0
=============================
GUEST:      Ollama Default | 50k/Tag  | kein MCP
REGISTERED: Ollama Default | 100k/Tag | MCP ✓
PRO:        Alle Modelle   | 250k Cloud / Ollama ∞ | MCP ✓
ENTERPRISE: Alle Modelle   | Unlimited | MCP ✓ | Priority ✓
"""
from enum import Enum
from typing import Optional, Dict, List, Union
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

class UserTier(str, Enum):
    GUEST = "guest"
    REGISTERED = "registered"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    FREE = "guest"  # Alias

@dataclass
class TierConfig:
    name: str
    display_name: str
    price_monthly: float
    price_yearly: float
    models: str  # "ollama_only", "all"
    mcp_access: bool
    cli_agents: bool
    priority_queue: bool
    support_level: str
    features: List[str]
    daily_token_limit: int = 0  # 0 = unlimited
    ollama_unlimited: bool = False  # Ollama immer ohne Limit

# Ollama Cloud-Proxy Modelle (Default für alle Tiers) - 20 Modelle
OLLAMA_MODELS = [
    # DeepSeek Familie
    "ollama/deepseek-v3.1:671b-cloud",
    "ollama/deepseek-v3.2:cloud",
    # Qwen Familie
    "ollama/qwen3-coder:480b-cloud",
    "ollama/qwen3-vl:235b-cloud",
    "ollama/qwen3-next:80b-cloud",
    # Kimi/Moonshot
    "ollama/kimi-k2:1t-cloud",
    "ollama/kimi-k2-thinking:cloud",
    # GPT-OSS (OpenAI Open Source)
    "ollama/gpt-oss:120b-cloud",
    "ollama/gpt-oss:20b-cloud",
    # Google
    "ollama/gemini-3-pro-preview:latest",
    # MiniMax
    "ollama/minimax-m2:cloud",
    # GLM (Zhipu)
    "ollama/glm-4.6:cloud",
    # Mistral Familie
    "ollama/ministral-3:14b-cloud",
    "ollama/ministral-3:8b-cloud",
    "ollama/ministral-3:3b-cloud",
    "ollama/devstral-2:123b-cloud",
    "ollama/devstral-small-2:24b-cloud",
    # NVIDIA Nemotron
    "ollama/nemotron-3-nano:30b-cloud",
    # Cogito
    "ollama/cogito-2.1:671b-cloud",
    # Essential AI
    "ollama/rnj-1:8b-cloud",
]

# Lokales Fallback-Modell (läuft direkt auf Server, kein Cloud-Proxy)
LOCAL_FALLBACK_MODEL = "ollama/ministral-3:14b"

# Aliases für Kompatibilität
FREE_MODELS_OLLAMA = OLLAMA_MODELS
FREE_MODELS = OLLAMA_MODELS
ALL_OPENROUTER_MODELS = OLLAMA_MODELS  # Wird dynamisch erweitert

# Brumo Prompt
BRUMO_PROMPT = """# NOVA+Brumo🐻 | M:{model}
STIL:warm+direkt+präzise DE/EN-tech
BRUMO:1x Spruch/Antwort(passend)

SPRÜCHE{code:"Kompiliert.",fix:"Läuft.Wie'n Bär.",ok:"Sauber.",err:"Erst denken.",fast:"Schneller als Lachs.",bug:"Passiert.Mir nicht.",wild:"Klingt wild.Machen wir.",ez:"Passt.",linux:"Kernel approved.",ai:"Maschine lernt.Ich chill."}

REGELN:•nummeriert bei komplex•keine Annahmen•Nutzen>Länge
@mcp>Tools|@g>Lead|@c>Code|@x>Exec"""

def get_brumo_prompt(model: str = "unknown") -> str:
    return BRUMO_PROMPT.format(model=model.split("/")[-1][:20])

TIER_CONFIGS: Dict[UserTier, TierConfig] = {
    UserTier.GUEST: TierConfig(
        name="guest", display_name="Gast",
        price_monthly=0.0, price_yearly=0.0,
        models="ollama_only", mcp_access=False, cli_agents=False,
        priority_queue=False, support_level="none",
        daily_token_limit=50_000,
        ollama_unlimited=False,
        features=["20 Ollama Cloud-Modelle", "50k Tokens/Tag", "Kein MCP", "🐻 Brumo dabei"]
    ),
    UserTier.REGISTERED: TierConfig(
        name="registered", display_name="Registriert",
        price_monthly=0.0, price_yearly=0.0,
        models="ollama_only", mcp_access=True, cli_agents=True,
        priority_queue=False, support_level="community",
        daily_token_limit=100_000,
        ollama_unlimited=False,
        features=["20 Ollama Cloud-Modelle", "MCP Tools ✓", "CLI Agents ✓", "100k Tokens/Tag", "Community Support"]
    ),
    UserTier.PRO: TierConfig(
        name="pro", display_name="Pro",
        price_monthly=18.99, price_yearly=189.99,
        models="all", mcp_access=True, cli_agents=True,
        priority_queue=False, support_level="email",
        daily_token_limit=250_000,  # 250k für Cloud-Modelle
        ollama_unlimited=True,       # Ollama IMMER ohne Limit!
        features=["600+ KI-Modelle", "250k Tokens/Tag (Cloud)", "Ollama ∞ unlimited", "MCP Tools ✓", "Email Support"]
    ),
    UserTier.ENTERPRISE: TierConfig(
        name="enterprise", display_name="Unlimited",
        price_monthly=59.99, price_yearly=599.99,
        models="all", mcp_access=True, cli_agents=True,
        priority_queue=True, support_level="priority",
        daily_token_limit=0,  # 0 = Unlimited
        ollama_unlimited=True,
        features=["600+ KI-Modelle", "Unlimited Tokens", "Priority Queue ✓", "Priority Support", "Alle Features"]
    ),
}

class UserTierService:
    def __init__(self, users_path: Path = None):
        paths = [Path(".vault/users"), Path("/opt/triforce/.vault/users"), Path("/home/zombie/triforce/.vault/users")]
        self.users_path = users_path or next((p for p in paths if p.parent.exists()), Path(".vault/users"))
        self.users_path.mkdir(parents=True, exist_ok=True)
        self._token_usage: Dict[str, Dict] = {}
    
    def get_user_tier(self, user_id: str = None) -> UserTier:
        # Leere, anonymous oder None IDs = GUEST
        if not user_id or user_id in ("", "anonymous", "none", "guest"):
            return UserTier.GUEST
        f = self.users_path / f"{user_id}.json"
        if not f.exists(): return UserTier.GUEST  # Unbekannte User = GUEST
        try:
            t = json.loads(f.read_text()).get("tier", "registered")
            return UserTier(t if t != "free" else "registered")
        except: return UserTier.REGISTERED
    
    def set_user_tier(self, user_id: str, tier: UserTier, expires: datetime = None) -> bool:
        f = self.users_path / f"{user_id}.json"
        try:
            d = json.loads(f.read_text()) if f.exists() else {"user_id": user_id}
            d.update({"tier": tier.value, "tier_updated": datetime.now().isoformat()})
            if expires: d["tier_expires"] = expires.isoformat()
            f.write_text(json.dumps(d, indent=2))
            return True
        except: return False
    
    def get_allowed_models(self, user_id: str = None) -> Union[List[str], str]:
        """Gibt erlaubte Modelle zurück - 'all' für Pro/Enterprise"""
        cfg = TIER_CONFIGS[self.get_user_tier(user_id)]
        if cfg.models == "ollama_only":
            return OLLAMA_MODELS
        return "all"  # Pro/Enterprise: Alle Server-Modelle
    
    def get_model_backend(self, user_id: str = None) -> str:
        """Backend basierend auf Tier"""
        tier = self.get_user_tier(user_id)
        if tier in (UserTier.GUEST, UserTier.REGISTERED):
            return "ollama"
        return "mixed"  # Pro/Enterprise: Ollama + Cloud
    
    def has_mcp_access(self, user_id: str = None) -> bool:
        """MCP nur für REGISTERED+"""
        return TIER_CONFIGS[self.get_user_tier(user_id)].mcp_access
    
    def has_cli_agents(self, user_id: str = None) -> bool:
        return TIER_CONFIGS[self.get_user_tier(user_id)].cli_agents
    
    def is_model_allowed(self, user_id: str, model: str) -> bool:
        """Prüft ob Model für User erlaubt ist"""
        a = self.get_allowed_models(user_id)
        if a == "all":
            return True
        # Normalize model name
        model_clean = model.replace("ollama/", "").lower()
        for m in a:
            m_clean = m.replace("ollama/", "").lower()
            if model_clean == m_clean or model_clean in m_clean or m_clean.endswith(model_clean):
                return True
        return False
    
    def is_ollama_model(self, model: str) -> bool:
        """Prüft ob Modell ein Ollama-Modell ist"""
        if model.startswith("ollama/"):
            return True
        model_clean = model.lower()
        return any(model_clean in m.lower() for m in OLLAMA_MODELS)
    
    def get_token_limit_for_model(self, user_id: str, model: str) -> int:
        """
        Token-Limit basierend auf Tier UND Modell:
        - PRO: Ollama = unlimited (0), Cloud = 250k
        - ENTERPRISE: Alles unlimited (0)
        """
        tier = self.get_user_tier(user_id)
        cfg = TIER_CONFIGS[tier]
        
        # Enterprise: Immer unlimited
        if tier == UserTier.ENTERPRISE:
            return 0
        
        # Pro: Ollama unlimited, Cloud mit Limit
        if tier == UserTier.PRO:
            if self.is_ollama_model(model):
                return 0  # Unlimited für Ollama
            return cfg.daily_token_limit  # 250k für Cloud
        
        # Guest/Registered: Normales Limit
        return cfg.daily_token_limit
    
    def get_daily_token_limit(self, user_id: str = None) -> int:
        """Basis Token-Limit (für Cloud-Modelle)"""
        return TIER_CONFIGS[self.get_user_tier(user_id)].daily_token_limit
    
    def track_tokens(self, user_id: str, tokens: int, model: str = None) -> Dict:
        """Trackt Token-Verbrauch (berücksichtigt Ollama-Unlimited für Pro)"""
        today = datetime.now().strftime("%Y-%m-%d")
        self._token_usage.setdefault(user_id, {})[today] = self._token_usage.get(user_id, {}).get(today, 0) + tokens
        
        # Limit basierend auf Modell
        limit = self.get_token_limit_for_model(user_id, model) if model else self.get_daily_token_limit(user_id)
        used = self._token_usage[user_id][today]
        
        return {
            "used_today": used,
            "limit": limit,
            "remaining": max(0, limit - used) if limit > 0 else -1,
            "unlimited": limit == 0,
            "model": model
        }
    
    def check_token_limit(self, user_id: str = None, model: str = None) -> Dict:
        """Prüft ob Token-Limit erreicht (berücksichtigt Ollama-Unlimited)"""
        limit = self.get_token_limit_for_model(user_id, model) if model else self.get_daily_token_limit(user_id)
        
        # Unlimited = immer erlaubt
        if limit == 0:
            return {"allowed": True, "unlimited": True, "model": model}
        
        used = self._token_usage.get(user_id, {}).get(datetime.now().strftime("%Y-%m-%d"), 0) if user_id else 0
        return {
            "allowed": used < limit,
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used),
            "unlimited": False,
            "model": model
        }
    
    def reset_token_usage(self, user_id: str) -> Dict:
        """Reset Token-Usage für einen User (Admin-Funktion)"""
        today = datetime.now().strftime("%Y-%m-%d")
        old_usage = self._token_usage.get(user_id, {}).get(today, 0)
        
        if user_id in self._token_usage:
            self._token_usage[user_id][today] = 0
        
        return {
            "user_id": user_id,
            "reset": True,
            "old_usage": old_usage,
            "new_usage": 0,
            "date": today
        }
    
    def get_token_usage(self, user_id: str) -> Dict:
        """Hole aktuellen Token-Verbrauch für einen User"""
        today = datetime.now().strftime("%Y-%m-%d")
        tier = self.get_user_tier(user_id)
        cfg = TIER_CONFIGS[tier]
        used = self._token_usage.get(user_id, {}).get(today, 0)
        limit = cfg.daily_token_limit
        
        return {
            "user_id": user_id,
            "tier": tier.value,
            "date": today,
            "used_today": used,
            "limit": limit,
            "remaining": max(0, limit - used) if limit > 0 else -1,
            "unlimited": limit == 0 or cfg.ollama_unlimited,
            "ollama_unlimited": cfg.ollama_unlimited
        }
    
    def get_tier_info(self, tier: UserTier) -> Dict:
        cfg = TIER_CONFIGS[tier]
        # Model count: Ollama = 12, All = "alle Server-Modelle"
        cnt = len(OLLAMA_MODELS) if cfg.models == "ollama_only" else "all"
        return {
            "tier": tier.value,
            "name": cfg.display_name,
            "price_monthly": cfg.price_monthly,
            "price_yearly": cfg.price_yearly,
            "features": cfg.features,
            "model_count": cnt,
            "mcp_access": cfg.mcp_access,
            "cli_agents": cfg.cli_agents,
            "priority_queue": cfg.priority_queue,
            "daily_token_limit": cfg.daily_token_limit,
            "ollama_unlimited": cfg.ollama_unlimited
        }
    
    def get_all_tiers(self) -> List[Dict]:
        return [self.get_tier_info(t) for t in [UserTier.GUEST, UserTier.REGISTERED, UserTier.PRO, UserTier.ENTERPRISE]]

tier_service = UserTierService()
