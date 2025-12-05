"""
TriStar Settings API Routes
Endpoints for managing global settings, model configs, and agent configs.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
import secrets

from ..config import get_settings
from ..services.tristar.settings_controller import settings_controller

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tristar/settings", tags=["TriStar Settings"])

# Security
security = HTTPBasic()


def verify_settings_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Verify credentials for settings access"""
    app_settings = get_settings()
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        app_settings.tristar_gui_user.encode("utf8")
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        app_settings.tristar_gui_password.encode("utf8")
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Ungültige Anmeldedaten",
            headers={"WWW-Authenticate": "Basic realm='TriStar Settings'"},
        )
    return credentials.username


# =============================================================================
# Request/Response Models
# =============================================================================

class GlobalSettingsUpdate(BaseModel):
    """Update global settings"""
    request_timeout: Optional[float] = Field(None, ge=1.0, le=300.0)
    ollama_timeout_ms: Optional[int] = Field(None, ge=1000, le=600000)
    max_concurrent_requests: Optional[int] = Field(None, ge=1, le=100)
    request_queue_timeout: Optional[float] = Field(None, ge=1.0, le=120.0)

    default_temperature_ollama: Optional[float] = Field(None, ge=0.0, le=2.0)
    default_temperature_gemini: Optional[float] = Field(None, ge=0.0, le=2.0)
    default_temperature_mistral: Optional[float] = Field(None, ge=0.0, le=2.0)
    default_temperature_anthropic: Optional[float] = Field(None, ge=0.0, le=2.0)
    default_temperature_huggingface: Optional[float] = Field(None, ge=0.0, le=2.0)

    rate_limit_requests_per_minute: Optional[int] = Field(None, ge=1, le=1000)
    rate_limit_tokens_per_minute: Optional[int] = Field(None, ge=1000, le=10000000)

    chain_max_cycles: Optional[int] = Field(None, ge=1, le=100)
    chain_default_aggressive: Optional[bool] = None
    chain_timeout_seconds: Optional[int] = Field(None, ge=30, le=3600)

    memory_max_entries: Optional[int] = Field(None, ge=100, le=1000000)
    memory_min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    memory_auto_prune: Optional[bool] = None

    log_level: Optional[str] = Field(None, pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_retention_days: Optional[int] = Field(None, ge=1, le=365)
    log_max_entries: Optional[int] = Field(None, ge=1000, le=1000000)

    gui_theme: Optional[str] = Field(None, pattern="^(dark|light|auto)$")
    gui_auto_refresh_seconds: Optional[int] = Field(None, ge=1, le=60)
    gui_show_debug: Optional[bool] = None

    crawler_enabled: Optional[bool] = None
    crawler_max_memory_bytes: Optional[int] = Field(None, ge=1048576, le=4294967296)
    crawler_flush_interval: Optional[int] = Field(None, ge=60, le=86400)
    crawler_retention_days: Optional[int] = Field(None, ge=1, le=365)

    wordpress_category_id: Optional[int] = Field(None, ge=0)
    wordpress_auto_publish: Optional[bool] = None

    default_chat_model: Optional[str] = None
    default_code_model: Optional[str] = None
    default_embedding_model: Optional[str] = None


class ModelConfigUpdate(BaseModel):
    """Update model configuration"""
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    priority: Optional[int] = Field(None, ge=0, le=100)
    enabled: Optional[bool] = None
    max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class AgentConfigUpdate(BaseModel):
    """Update agent configuration"""
    display_name: Optional[str] = None
    default_model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    system_prompt_override: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    auto_start: Optional[bool] = None
    timeout_seconds: Optional[int] = Field(None, ge=10, le=600)


class BulkModelConfigUpdate(BaseModel):
    """Bulk update model configurations"""
    models: Dict[str, ModelConfigUpdate]


class BulkAgentConfigUpdate(BaseModel):
    """Bulk update agent configurations"""
    agents: Dict[str, AgentConfigUpdate]


class APIKeyUpdate(BaseModel):
    """Update a single API key"""
    key_name: str = Field(..., description="Name of the API key field")
    value: str = Field(..., description="New value for the API key")


class BulkAPIKeyUpdate(BaseModel):
    """Bulk update API keys"""
    keys: Dict[str, str] = Field(..., description="Key-value pairs of API keys to update")


class FallbackConfigUpdate(BaseModel):
    """Update fallback configuration"""
    fallback_order: Optional[str] = None
    auto_fallback_enabled: Optional[bool] = None
    max_retries_before_fallback: Optional[int] = Field(None, ge=0, le=10)
    retry_delay_base: Optional[float] = Field(None, ge=0.1, le=10.0)
    fallback_timeout: Optional[float] = Field(None, ge=5.0, le=300.0)
    gemini_fallback_model: Optional[str] = None
    anthropic_fallback_model: Optional[str] = None
    ollama_fallback_model: Optional[str] = None
    mistral_fallback_model: Optional[str] = None
    circuit_breaker_enabled: Optional[bool] = None
    circuit_breaker_threshold: Optional[int] = Field(None, ge=1, le=100)
    circuit_breaker_timeout: Optional[int] = Field(None, ge=10, le=600)


class CachingConfigUpdate(BaseModel):
    """Update caching configuration"""
    cache_enabled: Optional[bool] = None
    cache_backend: Optional[str] = Field(None, pattern="^(memory|redis)$")
    cache_ttl_seconds: Optional[int] = Field(None, ge=60, le=86400)
    cache_max_entries: Optional[int] = Field(None, ge=100, le=100000)
    cache_identical_prompts: Optional[bool] = None
    cache_embeddings: Optional[bool] = None
    cache_embeddings_ttl: Optional[int] = Field(None, ge=60, le=604800)
    cache_exclude_models: Optional[str] = None
    cache_min_prompt_length: Optional[int] = Field(None, ge=1, le=1000)


# =============================================================================
# Global Settings Endpoints
# =============================================================================

@router.get("")
async def get_all_settings(user: str = Depends(verify_settings_auth)) -> Dict[str, Any]:
    """Get all settings (global, models, agents)"""
    return await settings_controller.get_all_settings()


@router.get("/global")
async def get_global_settings(user: str = Depends(verify_settings_auth)) -> Dict[str, Any]:
    """Get global settings only"""
    return await settings_controller.get_global_settings()


@router.put("/global")
async def update_global_settings(
    updates: GlobalSettingsUpdate,
    user: str = Depends(verify_settings_auth)
) -> Dict[str, Any]:
    """Update global settings"""
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="Keine Änderungen angegeben")

    return await settings_controller.update_global_settings(update_dict, modified_by=user)


@router.post("/reset")
async def reset_settings(user: str = Depends(verify_settings_auth)) -> Dict[str, Any]:
    """Reset all settings to defaults"""
    return await settings_controller.reset_to_defaults()


@router.get("/export")
async def export_settings(user: str = Depends(verify_settings_auth)) -> Dict[str, Any]:
    """Export all settings for backup"""
    return await settings_controller.export_settings()


@router.post("/import")
async def import_settings(
    data: Dict[str, Any],
    user: str = Depends(verify_settings_auth)
) -> Dict[str, Any]:
    """Import settings from backup"""
    return await settings_controller.import_settings(data)


# =============================================================================
# Model Configuration Endpoints
# =============================================================================

@router.get("/models")
async def get_model_configs(user: str = Depends(verify_settings_auth)) -> Dict[str, Any]:
    """Get all model configurations"""
    return {
        "models": await settings_controller.get_model_configs(),
        "count": len(await settings_controller.get_model_configs())
    }


@router.get("/models/by-priority")
async def get_models_by_priority(
    min_priority: int = Query(0, ge=0, le=100),
    user: str = Depends(verify_settings_auth)
) -> Dict[str, Any]:
    """Get models sorted by priority"""
    models = await settings_controller.get_models_by_priority(min_priority)
    return {"models": models, "count": len(models)}


@router.get("/models/{model_id:path}")
async def get_model_config(
    model_id: str,
    user: str = Depends(verify_settings_auth)
) -> Dict[str, Any]:
    """Get configuration for a specific model"""
    config = await settings_controller.get_model_config(model_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Model {model_id} nicht konfiguriert")
    return config


@router.put("/models/{model_id:path}")
async def update_model_config(
    model_id: str,
    updates: ModelConfigUpdate,
    user: str = Depends(verify_settings_auth)
) -> Dict[str, Any]:
    """Update configuration for a model"""
    return await settings_controller.set_model_config(
        model_id=model_id,
        **{k: v for k, v in updates.model_dump().items() if v is not None}
    )


@router.delete("/models/{model_id:path}")
async def delete_model_config(
    model_id: str,
    user: str = Depends(verify_settings_auth)
) -> Dict[str, Any]:
    """Delete model configuration"""
    success = await settings_controller.delete_model_config(model_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Model {model_id} nicht gefunden")
    return {"success": True, "deleted": model_id}


@router.put("/models")
async def bulk_update_model_configs(
    updates: BulkModelConfigUpdate,
    user: str = Depends(verify_settings_auth)
) -> Dict[str, Any]:
    """Bulk update multiple model configurations"""
    results = {}
    for model_id, config in updates.models.items():
        results[model_id] = await settings_controller.set_model_config(
            model_id=model_id,
            **{k: v for k, v in config.model_dump().items() if v is not None}
        )
    return {"updated": len(results), "models": results}


# =============================================================================
# Agent Configuration Endpoints
# =============================================================================

@router.get("/agents")
async def get_agent_configs(user: str = Depends(verify_settings_auth)) -> Dict[str, Any]:
    """Get all agent configurations"""
    return {
        "agents": await settings_controller.get_agent_configs(),
        "count": len(await settings_controller.get_agent_configs())
    }


@router.get("/agents/{agent_id}")
async def get_agent_config(
    agent_id: str,
    user: str = Depends(verify_settings_auth)
) -> Dict[str, Any]:
    """Get configuration for a specific agent"""
    config = await settings_controller.get_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} nicht konfiguriert")
    return config


@router.put("/agents/{agent_id}")
async def update_agent_config(
    agent_id: str,
    updates: AgentConfigUpdate,
    user: str = Depends(verify_settings_auth)
) -> Dict[str, Any]:
    """Update configuration for an agent"""
    return await settings_controller.set_agent_config(
        agent_id=agent_id,
        **{k: v for k, v in updates.model_dump().items() if v is not None}
    )


@router.put("/agents")
async def bulk_update_agent_configs(
    updates: BulkAgentConfigUpdate,
    user: str = Depends(verify_settings_auth)
) -> Dict[str, Any]:
    """Bulk update multiple agent configurations"""
    results = {}
    for agent_id, config in updates.agents.items():
        results[agent_id] = await settings_controller.set_agent_config(
            agent_id=agent_id,
            **{k: v for k, v in config.model_dump().items() if v is not None}
        )
    return {"updated": len(results), "agents": results}


# =============================================================================
# Quick Access Endpoints (no auth for reading defaults)
# =============================================================================

@router.get("/temperature/{model_id:path}", tags=["Quick Access"])
async def get_model_temperature(model_id: str) -> Dict[str, Any]:
    """Get temperature for a model (public endpoint for LLM calls)"""
    temp = await settings_controller.get_model_temperature(model_id)
    return {"model_id": model_id, "temperature": temp}


@router.get("/agent-temperature/{agent_id}", tags=["Quick Access"])
async def get_agent_temperature(agent_id: str) -> Dict[str, Any]:
    """Get temperature for an agent (public endpoint)"""
    temp = await settings_controller.get_agent_temperature(agent_id)
    return {"agent_id": agent_id, "temperature": temp}


# =============================================================================
# API Keys Endpoints
# =============================================================================

@router.get("/api-keys")
async def get_api_keys(user: str = Depends(verify_settings_auth)) -> Dict[str, Any]:
    """Get all API keys (masked)"""
    return {
        "api_keys": await settings_controller.get_api_keys(mask_secrets=True),
        "note": "Sensitive values are masked. Use PUT to update."
    }


@router.put("/api-keys/{key_name}")
async def update_api_key(
    key_name: str,
    update: APIKeyUpdate,
    user: str = Depends(verify_settings_auth)
) -> Dict[str, Any]:
    """Update a single API key"""
    try:
        result = await settings_controller.set_api_key(update.key_name, update.value, modified_by=user)
        return {"success": True, "api_keys": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/api-keys")
async def update_api_keys(
    updates: BulkAPIKeyUpdate,
    user: str = Depends(verify_settings_auth)
) -> Dict[str, Any]:
    """Bulk update multiple API keys"""
    result = await settings_controller.set_api_keys(updates.keys, modified_by=user)
    return {"success": True, "updated": len(updates.keys), "api_keys": result}


@router.get("/api-keys/verify/{provider}")
async def verify_api_key(
    provider: str,
    user: str = Depends(verify_settings_auth)
) -> Dict[str, Any]:
    """Verify if an API key is configured for a provider"""
    return await settings_controller.verify_api_key(provider)


@router.get("/api-keys/status")
async def get_api_keys_status(user: str = Depends(verify_settings_auth)) -> Dict[str, Any]:
    """Get status of all configured API keys"""
    providers = ["gemini", "anthropic", "mistral", "huggingface", "gpt_oss", "ollama"]
    status = {}
    for provider in providers:
        status[provider] = await settings_controller.verify_api_key(provider)
    return {"providers": status}


# =============================================================================
# Fallback Configuration Endpoints
# =============================================================================

@router.get("/fallback")
async def get_fallback_config(user: str = Depends(verify_settings_auth)) -> Dict[str, Any]:
    """Get fallback configuration"""
    return await settings_controller.get_fallback_config()


@router.put("/fallback")
async def update_fallback_config(
    updates: FallbackConfigUpdate,
    user: str = Depends(verify_settings_auth)
) -> Dict[str, Any]:
    """Update fallback configuration"""
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="Keine Änderungen angegeben")
    return await settings_controller.update_fallback_config(update_dict)


# =============================================================================
# Caching Configuration Endpoints
# =============================================================================

@router.get("/caching")
async def get_caching_config(user: str = Depends(verify_settings_auth)) -> Dict[str, Any]:
    """Get caching configuration"""
    return await settings_controller.get_caching_config()


@router.put("/caching")
async def update_caching_config(
    updates: CachingConfigUpdate,
    user: str = Depends(verify_settings_auth)
) -> Dict[str, Any]:
    """Update caching configuration"""
    update_dict = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="Keine Änderungen angegeben")
    return await settings_controller.update_caching_config(update_dict)
