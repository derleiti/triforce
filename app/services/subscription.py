"""
AILinux Subscription v3.0 — Swarm Edition
FREE         = Ollama + Free-Tier — grosszuegiges Limit
SUBSCRIPTION = 35EUR/month — alle 600+ Modelle + Swarm CLI
SOFTWARE     = Einzelkauf-Produkte (Copa OCR etc.) — einmal bezahlt, inkl. Updates
"""
from __future__ import annotations
import logging, os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum

logger = logging.getLogger("ailinux.subscription")
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    import redis as _rl
    _redis = _rl.from_url(_REDIS_URL, decode_responses=True)
    _redis.ping()
except Exception as _e:
    logger.warning(f"Redis unavailable for quota: {_e}")
    _redis = None

class PlanType(str, Enum):
    FREE         = "free"
    SUBSCRIPTION = "subscription"
    SOFTWARE     = "software"
    # Legacy aliases
    DEMO         = "free"
    SUBSCRIBER   = "subscription"

# Woechentliche Token-Limits — grosszuegig, Schutz gegen API-Scraper
WEEKLY_LIMITS = {
    PlanType.FREE:         200_000,    # ~40 normale Gespraeche/Woche
    PlanType.SUBSCRIPTION: 5_000_000,  # praktisch unlimitiert
    PlanType.SOFTWARE:     200_000,    # wie free (Einzelkauf = kein Abo)
}
CONTEXT_LIMITS = {
    PlanType.FREE: 8_192,
    PlanType.SUBSCRIPTION: 128_000,
    PlanType.SOFTWARE: 8_192,
}

# Free darf alle normalen Tools — gesperrt sind nur:
# Federation-Nodes (kostet Remote-Ressourcen) und Swarm-Koordination
# Tools gesperrt fuer free/software (brauchen Server-Ressourcen)
FREE_BLOCKED_TOOLS = {
    # Federation — nur Subscription
    "remote_admin", "remote_exec", "remote_task",
    # Swarm ueber Federation
    "mesh_task", "queue_research", "queue_broadcast",
    "group_chat_create", "group_chat_consolidate",
    "agent_broadcast", "swarm_broadcast",
    # Systemaenderungen
    "restart", "service_control", "package_manager",
}
# Backward compat
DEMO_BLOCKED_TOOLS = FREE_BLOCKED_TOOLS

def _iso_week_key(dt): return dt.strftime("%G-W%V")
def _week_reset_ts():
    now = datetime.now(timezone.utc)
    d = (7 - now.weekday()) % 7 or 7
    m = (now + timedelta(days=d)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int(m.timestamp())

@dataclass
class QuotaState:
    user_id: str; plan: PlanType; week_key: str
    tokens_used: int = 0; reset_at: int = 0
    @property
    def limit(self): return WEEKLY_LIMITS[self.plan]
    @property
    def remaining(self): return max(0, self.limit - self.tokens_used)
    @property
    def exhausted(self): return self.tokens_used >= self.limit
    def to_api(self):
        return {"plan": self.plan.value, "week": self.week_key,
                "tokens_used": self.tokens_used, "tokens_limit": self.limit,
                "remaining": self.remaining, "reset_at": self.reset_at,
                "reset_iso": datetime.fromtimestamp(self.reset_at, tz=timezone.utc).isoformat(),
                "exhausted": self.exhausted}

class SubscriptionService:
    def get_quota(self, user_id, plan):
        now = datetime.now(timezone.utc)
        wk = _iso_week_key(now); ra = _week_reset_ts()
        if _redis:
            try:
                raw = _redis.get(f"quota:{user_id}:{wk}")
                return QuotaState(user_id, plan, wk, int(raw) if raw else 0, ra)
            except Exception as e: logger.warning(f"quota read: {e}")
        return QuotaState(user_id, plan, wk, 0, ra)

    def consume(self, user_id, plan, tokens):
        now = datetime.now(timezone.utc)
        wk = _iso_week_key(now); ra = _week_reset_ts(); used = 0
        if _redis:
            try:
                k = f"quota:{user_id}:{wk}"
                used = _redis.incrby(k, tokens)
                _redis.expireat(k, ra + 3600)
            except Exception as e: logger.warning(f"quota write: {e}")
        return QuotaState(user_id, plan, wk, used, ra)

    def is_allowed(self, user_id, plan, est=100):
        return self.get_quota(user_id, plan).remaining >= est

    def is_tool_allowed(self, tool_name, plan):
        if plan == PlanType.SUBSCRIPTION:
            return True  # Subscriber duerfen alles
        return tool_name not in FREE_BLOCKED_TOOLS

    def get_context_limit(self, plan):
        return CONTEXT_LIMITS[plan]

subscription_service = SubscriptionService()

def tier_to_plan(tier_str):
    """
    Mappt beliebigen Tier/Role-String auf PlanType.
    Fail-safe: Unbekannt -> FREE.
    Quelle der Wahrheit fuer alle Komponenten.
    """
    t = (tier_str or "").strip().lower()
    _subscription = {"enterprise", "pro", "subscriber", "paid", "admin",
                     "superuser", "premium", "subscription", "unlimited"}
    _software = {"software"}
    _free = {"demo", "free", "guest", "anonymous", "trial", "registered", ""}
    if t in _subscription:
        return PlanType.SUBSCRIPTION
    if t in _software:
        return PlanType.SOFTWARE
    if t in _free:
        return PlanType.FREE
    logger.warning(f"Unknown tier string '{tier_str}', defaulting to FREE")
    return PlanType.FREE
