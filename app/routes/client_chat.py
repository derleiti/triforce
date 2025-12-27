"""
AILinux Client Chat API
Tier-basierter Chat:
- Free: Ollama Backend (lokal auf Server)
- Pro/Enterprise: OpenRouter + alle Cloud-Provider
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
import httpx
import os
import logging
import jwt
from datetime import datetime

from ..services.user_tiers import (
    tier_service, UserTier, FREE_MODELS_OLLAMA, LOCAL_FALLBACK_MODEL
)
from ..services.model_registry import registry
from ..services.model_availability import availability_service

logger = logging.getLogger("ailinux.client_chat")

router = APIRouter(prefix="/client", tags=["Client Chat"])

# Backend Config
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# JWT Config - Import from auth module to share secret
from .client_auth import JWT_SECRET, JWT_ALGORITHM


def extract_user_from_token(authorization: str = None) -> Optional[str]:
    """
    Extrahiert User-ID (Email) aus JWT Token.
    
    Der Token enthält:
    - email: User-Email (primärer Identifier für Tier-Service)
    - sub: Standard JWT subject (auch Email)
    - role: Tier (guest, registered, pro, enterprise)
    
    Returns: email oder None
    """
    if not authorization:
        return None
    
    try:
        # Bearer Token extrahieren
        token = authorization.replace("Bearer ", "").strip()
        if not token:
            return None
        
        # JWT dekodieren
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Email aus Token (primär)
        email = payload.get("email") or payload.get("sub")
        if email:
            logger.debug(f"Token valid: email={email}, role={payload.get('role')}")
            return email
        
        # Fallback: Role als Tier verwenden (für alte Tokens)
        role = payload.get("role", "guest")
        logger.warning(f"Token ohne Email, nutze role={role} als Fallback")
        return None
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT Token: {e}")
        return None
    except Exception as e:
        logger.error(f"Token extraction error: {e}")
        return None


def get_user_id_from_headers(
    authorization: str = None,
    x_user_id: str = None
) -> str:
    """
    Ermittelt User-ID aus Headers.
    Priorität:
    1. Authorization Bearer Token (JWT)
    2. X-User-ID Header
    3. "anonymous" (Guest)
    """
    # 1. Versuche JWT Token
    if authorization:
        user_from_token = extract_user_from_token(authorization)
        if user_from_token:
            return user_from_token
    
    # 2. Fallback auf X-User-ID Header
    if x_user_id and x_user_id not in ("", "anonymous", "none", "null"):
        return x_user_id
    
    # 3. Guest
    return "anonymous"


class ChatRequest(BaseModel):
    message: str
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
    model_count: int
    models: List[str]
    backend: str
    upgrade_available: bool


def get_default_ollama_model() -> str:
    """Default Ollama-Modell für alle Tiers (Cloud-Proxy)"""
    return "deepseek-v3.1:671b-cloud"


def get_default_model(tier: UserTier) -> str:
    """Default-Modell basierend auf Tier - ALLE nutzen Ollama Cloud-Proxy"""
    # Alle Tiers nutzen Ollama Cloud-Proxy (kostenlos, lokal gehostet)
    # OpenRouter Free-Modelle brauchen trotzdem Credits
    return "ollama/deepseek-v3.1:671b-cloud"


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
    """Call OpenRouter API (für Pro/Enterprise) mit Ollama-Fallback bei 402"""

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
                model="ollama/deepseek-v3.1:671b-cloud",
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

        return response.json()


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
    user_id = get_user_id_from_headers(authorization, x_user_id)
    logger.debug(f"Chat request: user={user_id}, auth={'yes' if authorization else 'no'}")

    # Tier holen
    tier = tier_service.get_user_tier(user_id)

    # Messages bauen
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
    model = request.model or get_default_model(tier)

    # === GUEST / REGISTERED: Nur Ollama ===
    if tier in (UserTier.GUEST, UserTier.REGISTERED):
        # Erzwinge Ollama-Prefix
        if not model.startswith("ollama/"):
            model = f"ollama/{model}"

        # Prüfen ob erlaubt
        if not tier_service.is_model_allowed(user_id, model):
            model = "ollama/deepseek-v3.1:671b-cloud"
            logger.warning(f"Model nicht erlaubt für {tier.value}, Fallback: {model}")

        # Token-Limit prüfen
        limit_check = tier_service.check_token_limit(user_id, model)
        if not limit_check["allowed"]:
            raise HTTPException(429, f"Token-Limit erreicht ({limit_check['limit']}/Tag)")

        # Ollama Call
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
            
            # PRO: Ollama = unlimited (kein Limit-Check nötig)
            result = await call_ollama(
                model=model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            backend = "ollama"
        else:
            # Cloud-Modelle: Token-Limit prüfen (außer Enterprise)
            if tier != UserTier.ENTERPRISE:
                limit_check = tier_service.check_token_limit(user_id, model)
                if not limit_check["allowed"]:
                    raise HTTPException(429, f"Token-Limit erreicht ({limit_check['limit']}/Tag). Nutze Ollama-Modelle für unlimited.")

            # OpenRouter-Prefix entfernen
            if model.startswith("openrouter/"):
                model = model[11:]

            # OpenRouter Call
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
    is_unlimited = (tier in (UserTier.PRO, UserTier.ENTERPRISE) and is_ollama) or tier == UserTier.ENTERPRISE

    # Tokens tracken - NUR bei erfolgreicher Operation und NICHT für unlimited Ollama
    if tokens and user_id != "anonymous" and response_text:
        # Pro mit Ollama = nicht tracken (unlimited)
        if not (tier == UserTier.PRO and is_ollama):
            tier_service.track_tokens(user_id, tokens, model)

    return ChatResponse(
        response=response_text,
        model=model,
        tier=tier.value,
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
    user_id = get_user_id_from_headers(authorization, x_user_id)
    logger.debug(f"Models request: user={user_id}")
    
    tier = tier_service.get_user_tier(user_id)
    config = tier_service.get_tier_info(tier)

    if tier in (UserTier.GUEST, UserTier.REGISTERED):
        # Guest/Registered: Nur Ollama Modelle
        models = FREE_MODELS_OLLAMA
        backend = "ollama"
    else:
        # Pro/Enterprise: Alle Server-Modelle
        all_models = await registry.list_models()
        all_ids = [m.id for m in all_models]
        # Filtere unavailable Models raus
        models = availability_service.filter_available(all_ids)
        # Stelle sicher dass Ollama-Modelle immer dabei sind
        for om in FREE_MODELS_OLLAMA:
            if om not in models:
                models.append(om)
        backend = "mixed"

    return ModelsResponse(
        tier=tier.value,
        tier_name=config["name"],
        model_count=len(models),
        models=models,
        backend=backend,
        upgrade_available=(tier in (UserTier.GUEST, UserTier.REGISTERED))
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
    user_id = get_user_id_from_headers(authorization, x_user_id)
    tier = tier_service.get_user_tier(user_id)
    info = tier_service.get_tier_info(tier)
    info["backend"] = "ollama" if tier == UserTier.GUEST else "openrouter"
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
    user_id = get_user_id_from_headers(authorization, x_user_id)
    tier = tier_service.get_user_tier(user_id)

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
    if tier == UserTier.GUEST:
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
    user_id = get_user_id_from_headers(authorization, x_user_id)
    return tier_service.get_token_usage(user_id)
