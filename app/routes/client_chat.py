"""
AILinux Client Chat API
Tier-basierter Chat:
- Free: Ollama Backend (lokal auf Server)
- Pro/Enterprise: OpenRouter + alle Cloud-Provider
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Union
import httpx
import os
import logging
from datetime import datetime

from ..services.user_tiers import (
    tier_service, UserTier, FREE_MODELS_OLLAMA, LOCAL_FALLBACK_MODEL,
    has_full_access, normalize_tier, is_free_tier,
)
from ..services.model_registry import registry
from ..services.model_availability import availability_service

logger = logging.getLogger("ailinux.client_chat")

router = APIRouter(prefix="/client", tags=["Client Chat"])

# Backend Config
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
from app.services.openrouter_budget import budget_guard

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

DEMO_MODE = (os.getenv("DEMO_MODE") or "false").strip().lower() in ("1","true","yes","on")

# JWT Config - Import from auth module to share secret
from .client_auth import JWT_SECRET, JWT_ALGORITHM, decode_jwt_token




def extract_user_and_tier_from_token(authorization: str = None) -> tuple:
    """
    Extrahiert User-ID (Email) UND Tier aus JWT Token.
    
    Returns: (email, tier) oder (None, None)
    Tier wird direkt aus Token genommen - kein DB-Lookup nötig.
    """
    if not authorization:
        return None, None
    
    try:
        token = authorization.replace("Bearer ", "").strip()
        if not token:
            return None, None
        
        # JWT mit Expiry-Check — abgelaufene Tokens werden NICHT akzeptiert
        try:
            payload = decode_jwt_token(token)
        except HTTPException as he:
            # Token expired oder ungültig → kein Tier-Zugang
            logger.warning(f"JWT rejected (expired/invalid): {he.detail}")
            return None, None
        
        email = payload.get("email") or payload.get("sub")
        tier = payload.get("role") or payload.get("tier")
        
        if email:
            logger.debug(f"Token valid: email={email}, tier={tier}")
            return email, tier
        
        return None, tier
        
    except HTTPException as e:
        logger.warning(f"JWT Token invalid/expired: {e.detail}")
        return None, None
    except Exception as e:
        logger.error(f"Token extraction error: {e}")
        return None, None


def get_user_and_tier_from_headers(
    authorization: str = None,
    x_user_id: str = None
) -> tuple:
    """
    Ermittelt User-ID und Tier aus Headers.
    
    Priorität:
    1. JWT Token (enthält beides - kein Lookup)
    2. X-User-ID + tier_service Lookup  
    3. "anonymous" + GUEST
    
    Returns: (user_id, UserTier)
    """
    # 1. JWT Token - Tier direkt aus Token
    if authorization:
        email, tier_str = extract_user_and_tier_from_token(authorization)
        if email:
            try:
                tier = normalize_tier(tier_str) if tier_str else tier_service.get_user_tier(email)
            except Exception:
                tier = tier_service.get_user_tier(email)
            return email, tier
    
    # 2. X-User-ID Header
    if x_user_id and x_user_id not in ("", "anonymous", "none", "null"):
        tier = tier_service.get_user_tier(x_user_id)
        return x_user_id, tier
    
    # 3. Guest
    return "anonymous", UserTier.FREE


# Legacy wrapper for compatibility
def extract_user_from_token(authorization: str = None) -> Optional[str]:
    """Legacy wrapper - use extract_user_and_tier_from_token instead."""
    email, _ = extract_user_and_tier_from_token(authorization)
    return email


def get_user_id_from_headers(authorization: str = None, x_user_id: str = None) -> str:
    """Legacy wrapper - use get_user_and_tier_from_headers instead."""
    user_id, _ = get_user_and_tier_from_headers(authorization, x_user_id)
    return user_id




class ChatRequest(BaseModel):
    message: str = ""
    messages: Optional[List[dict]] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096


class ChatResponse(BaseModel):
    response: str
    model: str
    tier: str
    backend: str  # "ollama" oder "openrouter"
    tokens_used: Optional[int] = None  # None bei Ollama für Pro (unlimited)
    tokens_unlimited: Optional[bool] = False  # True wenn Ollama für Pro/Enterprise
    latency_ms: Optional[int] = None
    fallback_used: Optional[bool] = False  # True wenn lokales Fallback-Modell verwendet wurde


class ModelsResponse(BaseModel):
    tier: str
    tier_name: str
    model_count: Union[int, str]  # FIX BE#19: DEMO_MODE returns "all"
    models: List[str]
    backend: str
    upgrade_available: bool


def get_default_ollama_model() -> str:
    """Default Ollama-Modell für alle Tiers (Cloud-Proxy)"""
    return "deepseek-v3.2:cloud"


def get_default_model(tier: UserTier) -> str:
    """Default-Modell basierend auf Tier - ALLE nutzen Ollama Cloud-Proxy"""
    # Alle Tiers nutzen Ollama Cloud-Proxy (kostenlos, lokal gehostet)
    # OpenRouter Free-Modelle brauchen trotzdem Credits
    return "ollama/deepseek-v3.2:cloud"


def normalize_ollama_model(model: str) -> str:
    """Normalisiere Model-ID für Ollama"""
    if model.startswith("ollama/"):
        return model[7:]  # Entferne "ollama/" Prefix
    return model


def normalize_openrouter_model(model: str) -> str:
    """Normalisiere Model-ID für OpenRouter"""
    if model.startswith("openrouter/"):
        return model[11:]  # Entferne "openrouter/" Prefix
    return model


async def call_ollama(
    model: str,
    messages: List[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    is_fallback: bool = False
) -> dict:
    """
    Call Ollama API (lokal auf Server)
    
    Bei Cloud-Proxy Fehlern (502, 503, Timeout) → Fallback auf lokales ministral-3:14b
    """

    # Normalisiere Model-Name
    model_name = normalize_ollama_model(model)

    payload = {
        "model": model_name,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload
            )

            # Cloud-Proxy Fehler → Fallback auf lokales Modell
            if response.status_code in (502, 503, 504) and not is_fallback:
                logger.warning(f"Ollama Cloud-Proxy Error {response.status_code} für {model} - Fallback auf lokales Modell")
                return await call_ollama(
                    model=LOCAL_FALLBACK_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    is_fallback=True
                )

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Ollama Error: {error_text}")
                
                # Bei anderen Fehlern auch Fallback versuchen
                if not is_fallback and "cloud" in model.lower():
                    logger.warning(f"Cloud-Modell {model} fehlgeschlagen - Fallback auf lokales Modell")
                    return await call_ollama(
                        model=LOCAL_FALLBACK_MODEL,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        is_fallback=True
                    )
                
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ollama Error: {error_text}"
                )

            result = response.json()

            # Ollama Response in OpenAI-Format konvertieren
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": result.get("message", {}).get("content", "")
                    }
                }],
                "usage": {
                    "total_tokens": result.get("eval_count", 0) + result.get("prompt_eval_count", 0)
                },
                "model_used": model_name,
                "is_fallback": is_fallback
            }

        except httpx.ConnectError:
            logger.error("Ollama nicht erreichbar")
            raise HTTPException(503, "Ollama Backend nicht erreichbar")
        except httpx.TimeoutException:
            # Timeout bei Cloud-Proxy → Fallback
            if not is_fallback and "cloud" in model.lower():
                logger.warning(f"Timeout für {model} - Fallback auf lokales Modell")
                return await call_ollama(
                    model=LOCAL_FALLBACK_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    is_fallback=True
                )
            raise HTTPException(504, "Ollama Timeout")


async def call_openrouter(
    model: str,
    messages: List[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096
) -> dict:
    """Call OpenRouter API (für Pro/Enterprise) mit Budget-Guard + Ollama-Fallback"""

    # Budget-Check: verhindert unkontrollierten Spend
    if not budget_guard.can_spend():
        logger.warning(f"OpenRouter budget exhausted - Fallback zu Ollama für {model}")
        return await call_ollama(
            model="ollama/qwen2.5:14b",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

    # Normalisiere Model-Name
    model_name = normalize_openrouter_model(model)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://ailinux.me",
        "X-Title": "AILinux Client"
    }

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload
        )

        # Bei 402 (Payment Required) → Fallback zu Ollama
        if response.status_code == 402:
            logger.warning(f"OpenRouter 402 für {model} - Fallback zu Ollama")
            # Markiere Model als unavailable
            availability_service.mark_error(model, 402, "Payment Required")
            # Fallback zu Ollama (kostenlos)
            return await call_ollama(
                model="ollama/deepseek-v3.2:cloud",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

        if response.status_code != 200:
            error_text = response.text
            raise HTTPException(
                status_code=response.status_code,
                detail=f"OpenRouter Error: {error_text}"
            )

        data = response.json()

        # Budget-Tracking: schätze Kosten aus Token-Usage
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        # Grobe Schätzung: $0.001/1K tokens (variiert je nach Modell)
        estimated_cost = (prompt_tokens + completion_tokens) / 1000 * 0.001
        if estimated_cost > 0:
            budget_guard.track_spend(estimated_cost)

        return data


async def call_github_models(
    model: str,
    messages: List[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096
) -> dict:
    """Call GitHub Models API — OpenAI-kompatibel, kostenlos mit Classic PAT."""
    import os, aiohttp
    token = os.getenv("GITHUB_MODELS_TOKEN", "")
    if not token:
        raise HTTPException(503, "GITHUB_MODELS_TOKEN nicht konfiguriert")

    # model-Format: github/meta/llama-3.3-70b-instruct → meta/llama-3.3-70b-instruct
    model_id = model[len("github/"):] if model.startswith("github/") else model

    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            "https://models.github.ai/inference/chat/completions",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/vnd.github+json",
            },
            json={
                "model": model_id,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                raise HTTPException(resp.status, f"GitHub Models error: {err[:200]}")
            data = await resp.json()
            content = data["choices"][0]["message"]["content"]
            return {
                "response": content,
                "model": model,
                "backend": "github",
                "usage": data.get("usage", {}),
            }


async def call_huggingface(
    model: str,
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict:
    """HuggingFace Inference API — OpenAI-kompatibel via router.huggingface.co."""
    import os, aiohttp
    token = os.getenv("HUGGINGFACE_API_KEY", "")
    if not token:
        raise HTTPException(503, "HUGGINGFACE_API_KEY nicht konfiguriert")

    # hf/org/model-name -> org/model-name
    model_id = model[len("hf/"):] if model.startswith("hf/") else model

    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            f"https://router.huggingface.co/hf-inference/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_id,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                raise HTTPException(resp.status, f"HuggingFace error: {err[:200]}")
            data = await resp.json()
            content = data["choices"][0]["message"]["content"]
            return {
                "response": content,
                "model": model,
                "backend": "huggingface",
                "usage": data.get("usage", {}),
            }


@router.post("/chat", response_model=ChatResponse)
async def client_chat(
    request: ChatRequest,
    authorization: str = Header(None, alias="Authorization"),
    x_user_id: str = Header(None, alias="X-User-ID"),
    x_client_id: str = Header(None, alias="X-Client-ID")
):
    """
    Chat-Endpoint für AILinux Client

    Tier-Routing:
    - GUEST: Ollama only, kein MCP, 50k/Tag
    - REGISTERED: Ollama only, MCP ✓, 100k/Tag
    - PRO: Alle Modelle, Ollama ∞, Cloud 250k/Tag
    - ENTERPRISE: Alle Modelle unlimited

    Headers (Priorität):
        1. Authorization: Bearer <JWT-Token> (aus /auth/login)
        2. X-User-ID: User-Email oder ID
        3. Ohne Header = Guest
    """
    start_time = datetime.now()

    # User-ID ermitteln (Token hat Priorität)
    user_id, tier = get_user_and_tier_from_headers(authorization, x_user_id)
    effective_tier = UserTier.SUBSCRIPTION if DEMO_MODE else normalize_tier(tier.value if hasattr(tier, 'value') else str(tier))
    tier_out = 'demo' if DEMO_MODE else effective_tier.value

    # DEMO_MODE: disable tier gating (treat everyone as subscription)
    if DEMO_MODE:
        tier = UserTier.SUBSCRIPTION
    logger.debug(f"Chat request: user={user_id}, auth={'yes' if authorization else 'no'}")


    # Messages bauen: messages-Array hat Prioritaet ueber message-String
    if request.messages:
        messages = list(request.messages)
        # System prompt prependen falls nicht schon vorhanden
        if request.system_prompt and (not messages or messages[0].get("role") != "system"):
            messages.insert(0, {"role": "system", "content": request.system_prompt})
    else:
        messages = []
        if request.system_prompt:
            messages.append({
                "role": "system",
                "content": request.system_prompt
            })
        messages.append({
            "role": "user",
            "content": request.message
        })

    # Model bestimmen

    model = request.model or get_default_model(effective_tier)


    force_or = (os.getenv("FORCE_GEMINI_OPENROUTER") or "").strip().lower() in ("1","true","yes","on")
    if (DEMO_MODE or force_or) and model.startswith("gemini/"):
        model = "openrouter/google/" + model.split("/", 1)[1]

    # DEMO_MODE: map native Gemini -> OpenRouter (native quota often 0)

    if DEMO_MODE and model.startswith("gemini/"):

        model = "openrouter/google/" + model.split("/", 1)[1]


    # === GUEST / REGISTERED: Nur Ollama + GitHub (kostenlos) ===

    if (not DEMO_MODE) and is_free_tier(tier):

        # GitHub Models sind kostenlos -> durchlassen
        # Alles andere: Erzwinge Ollama-Prefix

        if not model.startswith("ollama/") and not model.startswith("github/"):

            model = f"ollama/{model}"


        # Prüfen ob erlaubt

        if not tier_service.is_model_allowed(user_id, model):

            model = "ollama/deepseek-v3.2:cloud"

            logger.warning(f"Model nicht erlaubt für {tier.value}, Fallback: {model}")


        # Token-Limit prüfen

        limit_check = tier_service.check_token_limit(user_id, model)

        if not limit_check["allowed"]:

            raise HTTPException(429, f"Token-Limit erreicht ({limit_check['limit']}/Tag)")


        # GitHub Models (kostenlos) oder Ollama Call
        if model.startswith("github/"):
            result = await call_github_models(
                model=model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            backend = "github"
        else:
            result = await call_ollama(
                model=model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            backend = "ollama"


    # === PRO / ENTERPRISE: Alle Modelle ===

    else:

        # Ollama-Modelle direkt über Ollama

        if model.startswith("ollama/") or tier_service.is_ollama_model(model):

            if not model.startswith("ollama/"):

                model = f"ollama/{model}"


            result = await call_ollama(

                model=model,

                messages=messages,

                temperature=request.temperature,

                max_tokens=request.max_tokens

            )

            backend = "ollama"

        else:

            # Cloud-Modelle: Token-Limit prüfen (außer Enterprise)

            if not has_full_access(effective_tier):

                limit_check = tier_service.check_token_limit(user_id, model)

                if not limit_check["allowed"]:

                    raise HTTPException(429, f"Token-Limit erreicht ({limit_check['limit']}/Tag). Nutze Ollama-Modelle für unlimited.")


            _CHAT_ROUTER_PREFIXES = {"gemini", "anthropic", "openai", "mistral", "groq", "cerebras", "cloudflare", "github"}

            model_prefix = model.split("/")[0].lower() if "/" in model else ""


            if model.startswith("hf/"):

                result = await call_huggingface(

                    model=model,

                    messages=messages,

                    temperature=request.temperature,

                    max_tokens=request.max_tokens,

                )

                backend = "huggingface"


            elif model.startswith("github/"):

                result = await call_github_models(

                    model=model,

                    messages=messages,

                    temperature=request.temperature,

                    max_tokens=request.max_tokens

                )

                backend = "github"


            elif model.startswith("openrouter/"):

                result = await call_openrouter(

                    model=model[11:],

                    messages=messages,

                    temperature=request.temperature,

                    max_tokens=request.max_tokens

                )

                backend = "openrouter"


            elif model.startswith("cloudflare/"):
                # Cloudflare Workers AI — eigener Handler (nicht in api_proxy)
                from ..config import get_settings as _gs
                _s = _gs()
                if not _s.cloudflare_account_id or not _s.cloudflare_api_token:
                    raise HTTPException(503, "Cloudflare Workers AI nicht konfiguriert")
                from ..services.chat import _stream_cloudflare
                cf_model = model
                cf_chunks = []
                async for chunk in _stream_cloudflare(
                    cf_model, messages,
                    account_id=_s.cloudflare_account_id,
                    api_token=_s.cloudflare_api_token,
                    temperature=request.temperature,
                    stream=True, timeout=30.0,
                ):
                    cf_chunks.append(chunk)
                result = {
                    "choices": [{"message": {"role": "assistant", "content": "".join(cf_chunks)}}],
                    "usage": {"total_tokens": 0},
                    "model_used": model,
                }
                backend = "cloudflare"

            elif model_prefix in _CHAT_ROUTER_PREFIXES:

                from ..services.chat_router import api_proxy

                try:

                    response_str = await api_proxy.chat(

                        model=model,

                        messages=messages,

                        temperature=request.temperature,

                        max_tokens=request.max_tokens

                    )

                    result = {

                        "choices": [{"message": {"role": "assistant", "content": response_str}}],

                        "usage": {"total_tokens": 0},

                        "model_used": model,

                    }

                    backend = model_prefix

                except Exception as e:

                    err = str(e)

                    if ("RESOURCE_EXHAUSTED" in err or "Quota exceeded" in err or '"code": 429' in err):

                        if model.startswith("gemini/"):

                            availability_service.add_exclusion(model, "Google quota exhausted")

                        raise HTTPException(429, f"Provider-Fehler ({model_prefix}): {err}")

                    if "No API key" in err or "Vault" in err or "locked" in err:

                        raise HTTPException(400, f"Provider '{model_prefix}' nicht konfiguriert: API-Key fehlt. Nutze ein Ollama-Modell.")

                    raise HTTPException(502, f"Provider-Fehler ({model_prefix}): {err}")


            else:

                logger.warning(f"Unbekannter Model-Prefix '{model_prefix}' fuer '{model}', versuche OpenRouter")

                result = await call_openrouter(

                    model=model,

                    messages=messages,

                    temperature=request.temperature,

                    max_tokens=request.max_tokens

                )

                backend = "openrouter"



    # Response extrahieren
    response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    tokens = result.get("usage", {}).get("total_tokens")
    latency = int((datetime.now() - start_time).total_seconds() * 1000)
    fallback_used = result.get("is_fallback", False)
    
    # Bei Fallback: Model aktualisieren
    if fallback_used:
        model = f"ollama/{result.get('model_used', 'ministral-3:14b')}"

    # Prüfen ob Ollama unlimited (Pro/Enterprise mit Ollama-Modell)
    is_ollama = tier_service.is_ollama_model(model) or backend == "ollama"
    is_unlimited = has_full_access(effective_tier) or (has_full_access(effective_tier) and is_ollama)

    # Tokens tracken - NUR bei erfolgreicher Operation und NICHT für unlimited
    if (not DEMO_MODE) and tokens and user_id != "anonymous" and response_text:
        # Subscription = nicht tracken (unlimited)
        if not has_full_access(effective_tier):
            tier_service.track_tokens(user_id, tokens, model)

    return ChatResponse(
        response=response_text,
        model=model,
        tier=tier_out,
        backend=backend,
        tokens_used=tokens if not is_unlimited else None,  # Nicht anzeigen wenn unlimited
        tokens_unlimited=is_unlimited,
        latency_ms=latency,
        fallback_used=fallback_used
    )


@router.get("/models", response_model=ModelsResponse)
async def get_client_models(
    authorization: str = Header(None, alias="Authorization"),
    x_user_id: str = Header(None, alias="X-User-ID")
):
    """
    Hole verfügbare Modelle für den Client

    - Guest/Registered: Ollama Default (20 Modelle)
    - Pro/Enterprise: ALLE Server-Modelle + Ollama
    
    Headers (Priorität):
        1. Authorization: Bearer <JWT-Token>
        2. X-User-ID: User-Email
    """
    user_id, tier = get_user_and_tier_from_headers(authorization, x_user_id)
    logger.debug(f"Models request: user={user_id}")
    
    config = tier_service.get_tier_info(tier)

    if (not DEMO_MODE) and is_free_tier(tier):
        # Guest/Registered: Nur Ollama Modelle
        models = FREE_MODELS_OLLAMA
        backend = "ollama"
    else:
        # Pro/Enterprise: Alle Server-Modelle
        all_models = await registry.list_models()
        all_ids = [m.id for m in all_models]
        # Filtere unavailable Models raus
        models = availability_service.filter_available(all_ids)
        # DEMO_MODE: hide native Gemini models (quota often 0). Use OpenRouter Gemini instead.
        if DEMO_MODE:
            models = [m for m in models if not m.startswith('gemini/')]
        # Stelle sicher dass Ollama-Modelle immer dabei sind
        for om in FREE_MODELS_OLLAMA:
            if om not in models:
                models.append(om)
        backend = "mixed"

    return ModelsResponse(
      tier=("demo" if DEMO_MODE else tier.value),
      tier_name=("Demo" if DEMO_MODE else config["name"]),
        model_count=len(models),
        models=models,
        backend=backend,
      upgrade_available=(False if DEMO_MODE else is_free_tier(tier))
    )


@router.get("/tier")
async def get_client_tier(
    authorization: str = Header(None, alias="Authorization"),
    x_user_id: str = Header(None, alias="X-User-ID")
):
    """
    Hole Tier-Info für den aktuellen User
    
    Headers (Priorität):
        1. Authorization: Bearer <JWT-Token>
        2. X-User-ID: User-Email
    """
    user_id, tier = get_user_and_tier_from_headers(authorization, x_user_id)
    if DEMO_MODE:
        return {
            "tier": "demo",
            "name": "Demo",
            "price_monthly": 0.0,
            "price_yearly": 0.0,
            "features": ["Alle Modelle (via OpenRouter/Ollama)", "Native Gemini ausgeblendet (Quota=0)", "1 Woche Demo"],
            "model_count": "all",
            "mcp_access": True,
            "cli_agents": True,
            "priority_queue": False,
            "daily_token_limit": 0,
            "ollama_unlimited": True,
            "backend": "mixed",
            "user_id": user_id
        }

    info = tier_service.get_tier_info(tier)
    info["backend"] = "ollama" if is_free_tier(tier) else "openrouter"
    info["user_id"] = user_id  # Für Debug
    return info


@router.post("/analyze")
async def analyze_file(
    content: str,
    filename: str,
    action: str = "analyze",
    authorization: str = Header(None, alias="Authorization"),
    x_user_id: str = Header(None, alias="X-User-ID")
):
    """
    Datei-Analyse via KI

    Actions: analyze, bugs, optimize, summarize, document, security
    """
    user_id, tier = get_user_and_tier_from_headers(authorization, x_user_id)

    prompts = {
        "analyze": f"Analysiere diese Datei '{filename}' gründlich. Erkläre was sie tut, die Struktur und wichtige Teile:\n\n```\n{content[:8000]}\n```",
        "bugs": f"Finde Bugs, Fehler und potenzielle Probleme in '{filename}':\n\n```\n{content[:8000]}\n```",
        "optimize": f"Optimiere '{filename}'. Zeige verbesserten Code mit Erklärungen:\n\n```\n{content[:8000]}\n```",
        "summarize": f"Fasse '{filename}' kurz zusammen:\n\n```\n{content[:8000]}\n```",
        "document": f"Erstelle Dokumentation für '{filename}':\n\n```\n{content[:8000]}\n```",
        "security": f"Security-Check für '{filename}':\n\n```\n{content[:8000]}\n```",
    }

    prompt = prompts.get(action, prompts["analyze"])
    model = get_default_model(tier)
    messages = [{"role": "user", "content": prompt}]

    # Free: Ollama, Pro+: OpenRouter
    if is_free_tier(tier):
        result = await call_ollama(model, messages)
        backend = "ollama"
    else:
        result = await call_openrouter(normalize_openrouter_model(model), messages)
        backend = "openrouter"

    response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")

    return {
        "action": action,
        "filename": filename,
        "model": model,
        "tier": tier.value,
        "backend": backend,
        "result": response_text
    }


@router.get("/ollama/status")
async def ollama_status():
    """Prüfe Ollama Backend Status"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                return {
                    "status": "online",
                    "url": OLLAMA_BASE_URL,
                    "models_loaded": len(models),
                    "models": models[:20]  # Max 20 anzeigen
                }
    except Exception as e:
        logger.error(f"Ollama Status Check failed: {e}")

    return {
        "status": "offline",
        "url": OLLAMA_BASE_URL,
        "models_loaded": 0,
        "models": []
    }


# ========= MODEL AVAILABILITY ROUTES =========

@router.get("/models/availability")
async def get_model_availability():
    """
    Zeige Model-Availability Status
    - Excluded Models (Quota/Rate-Limit)  
    - Provider Health
    """
    return await availability_service.run_health_check()


@router.post("/models/availability/reset/{model_id:path}")
async def reset_model_availability(model_id: str):
    """Reset Availability-Status für ein Model (Admin)"""
    availability_service.reset_model(model_id)
    return {"reset": model_id, "status": "ok"}


@router.post("/models/availability/exclude")
async def exclude_model(model_id: str, reason: str = "manual"):
    """Manuell ein Model excluden (Admin)"""
    availability_service.add_exclusion(model_id, reason)
    return {"excluded": model_id, "reason": reason}


# ========= TOKEN MANAGEMENT ROUTES =========

@router.post("/tokens/reset/{user_id}")
async def reset_user_tokens(user_id: str):
    """Reset Token-Usage für einen User (Admin)"""
    result = tier_service.reset_token_usage(user_id)
    return result


@router.get("/tokens/usage/{user_id}")
async def get_user_token_usage(user_id: str):
    """Hole Token-Verbrauch für einen User"""
    return tier_service.get_token_usage(user_id)


@router.get("/tokens/usage")
async def get_current_user_token_usage(
    authorization: str = Header(None, alias="Authorization"),
    x_user_id: str = Header(None, alias="X-User-ID")
):
    """Hole eigenen Token-Verbrauch"""
    user_id, tier = get_user_and_tier_from_headers(authorization, x_user_id)
    return tier_service.get_token_usage(user_id)
