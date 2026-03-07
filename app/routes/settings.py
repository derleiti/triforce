from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi_limiter.depends import RateLimiter

from ..config import get_settings
from ..schemas.settings import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings_endpoint():
    """Get current system settings (read-only view)"""
    settings = get_settings()

    return SettingsResponse(
        # Core Settings
        request_timeout=settings.request_timeout,
        ollama_timeout_ms=settings.ollama_timeout_ms,
        max_concurrent_requests=settings.max_concurrent_requests,
        request_queue_timeout=settings.request_queue_timeout,
        # Backends
        ollama_base=str(settings.ollama_base),
        ollama_bearer_auth_enabled=settings.ollama_bearer_auth_enabled,
        gemini_api_key_configured=bool(settings.gemini_api_key),
        mistral_api_key_configured=bool(settings.mistral_api_key),
        gpt_oss_configured=bool(settings.gpt_oss_api_key and settings.gpt_oss_base_url),
        stable_diffusion_url=str(settings.stable_diffusion_url),
        comfyui_url=str(settings.comfyui_url) if settings.comfyui_url else None,
        stable_diffusion_backend=settings.stable_diffusion_backend,
        stable_diffusion_default_models=settings.stable_diffusion_default_models,
        # Crawler Configuration
        crawler_enabled=settings.crawler_enabled,
        crawler_max_memory_bytes=settings.crawler_max_memory_bytes,
        crawler_flush_interval=settings.crawler_flush_interval,
        crawler_retention_days=settings.crawler_retention_days,
        crawler_summary_model=settings.crawler_summary_model,
        # User Crawler Settings
        user_crawler_workers=settings.user_crawler_workers,
        user_crawler_max_concurrent=settings.user_crawler_max_concurrent,
        # Auto Crawler Settings
        auto_crawler_workers=settings.auto_crawler_workers,
        auto_crawler_enabled=settings.auto_crawler_enabled,
        # WordPress Integration
        wordpress_configured=bool(settings.wordpress_url and settings.wordpress_user),
        wordpress_url=str(settings.wordpress_url) if settings.wordpress_url else None,
        wordpress_category_id=settings.wordpress_category_id,
        # OpenAI Compatibility
        openai_model_aliases=settings.openai_model_aliases or {},
        # CORS
        cors_allowed_origins=settings.cors_allowed_origins,
    )


@router.put("", response_model=SettingsResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def update_settings_endpoint(updates: SettingsUpdate):
    """
    Update system settings (runtime configuration).
    Note: These changes are not persisted to .env file and will be lost on restart.
    """
    import os
    import json

    # Clear the settings cache to force reload
    get_settings.cache_clear()

    # Update environment variables for runtime changes
    # Core Settings
    if updates.request_timeout is not None:
        os.environ["REQUEST_TIMEOUT"] = str(updates.request_timeout)
    if updates.ollama_timeout_ms is not None:
        os.environ["OLLAMA_TIMEOUT_MS"] = str(updates.ollama_timeout_ms)
    if updates.max_concurrent_requests is not None:
        os.environ["MAX_CONCURRENT_REQUESTS"] = str(updates.max_concurrent_requests)
    if updates.request_queue_timeout is not None:
        os.environ["REQUEST_QUEUE_TIMEOUT"] = str(updates.request_queue_timeout)

    # Backend URLs
    if updates.ollama_base is not None:
        os.environ["OLLAMA_BASE"] = str(updates.ollama_base)
    if updates.stable_diffusion_url is not None:
        os.environ["STABLE_DIFFUSION_URL"] = str(updates.stable_diffusion_url)
    if updates.comfyui_url is not None:
        os.environ["COMFYUI_URL"] = str(updates.comfyui_url)
    if updates.wordpress_url is not None:
        os.environ["WORDPRESS_URL"] = str(updates.wordpress_url)

    # Backend Settings
    if updates.ollama_bearer_auth_enabled is not None:
        os.environ["OLLAMA_BEARER_AUTH_ENABLED"] = str(updates.ollama_bearer_auth_enabled).lower()
    if updates.stable_diffusion_backend is not None:
        os.environ["STABLE_DIFFUSION_BACKEND"] = updates.stable_diffusion_backend
    if updates.stable_diffusion_default_models is not None:
        os.environ["STABLE_DIFFUSION_DEFAULT_MODELS"] = updates.stable_diffusion_default_models

    # Crawler Configuration
    if updates.crawler_enabled is not None:
        os.environ["CRAWLER_ENABLED"] = str(updates.crawler_enabled).lower()
    if updates.crawler_max_memory_bytes is not None:
        os.environ["CRAWLER_MAX_MEMORY_BYTES"] = str(updates.crawler_max_memory_bytes)
    if updates.crawler_flush_interval is not None:
        os.environ["CRAWLER_FLUSH_INTERVAL"] = str(updates.crawler_flush_interval)
    if updates.crawler_retention_days is not None:
        os.environ["CRAWLER_RETENTION_DAYS"] = str(updates.crawler_retention_days)
    if updates.crawler_summary_model is not None:
        os.environ["CRAWLER_SUMMARY_MODEL"] = updates.crawler_summary_model

    # User Crawler Settings
    if updates.user_crawler_workers is not None:
        os.environ["USER_CRAWLER_WORKERS"] = str(updates.user_crawler_workers)
    if updates.user_crawler_max_concurrent is not None:
        os.environ["USER_CRAWLER_MAX_CONCURRENT"] = str(updates.user_crawler_max_concurrent)

    # Auto Crawler Settings
    if updates.auto_crawler_workers is not None:
        os.environ["AUTO_CRAWLER_WORKERS"] = str(updates.auto_crawler_workers)
    if updates.auto_crawler_enabled is not None:
        os.environ["AUTO_CRAWLER_ENABLED"] = str(updates.auto_crawler_enabled).lower()

    # WordPress Settings
    if updates.wordpress_category_id is not None:
        os.environ["WORDPRESS_CATEGORY_ID"] = str(updates.wordpress_category_id)

    # OpenAI Compatibility
    if updates.openai_model_aliases is not None:
        os.environ["OPENAI_MODEL_ALIASES"] = json.dumps(updates.openai_model_aliases)

    # CORS
    if updates.cors_allowed_origins is not None:
        os.environ["CORS_ALLOWED_ORIGINS"] = updates.cors_allowed_origins

    # Return updated settings
    return await get_settings_endpoint()
