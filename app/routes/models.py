from __future__ import annotations

from fastapi import APIRouter, Query

from ..services.model_registry import registry
from ..services.model_availability import availability_service

router = APIRouter(tags=["models"])


@router.get("/models")
async def list_models(
    force_refresh: bool = Query(False, description="Force-refresh the model registry"),
    include_unavailable: bool = Query(False, description="Include quota-exhausted models")
) -> dict[str, object]:
    """
    Liste alle verfügbaren Modelle.
    Modelle mit Quota-Problemen werden standardmäßig NICHT angezeigt.
    """
    models = await registry.list_models(force_refresh=force_refresh)
    
    if include_unavailable:
        # Admin-Modus: Alle Modelle zeigen
        return {
            "data": [model.to_dict() for model in models],
            "total": len(models),
            "filtered": False
        }
    
    # Standard: Nur verfügbare Modelle
    available_models = [
        model for model in models 
        if availability_service.is_available(model.id)
    ]
    
    excluded_count = len(models) - len(available_models)
    
    return {
        "data": [model.to_dict() for model in available_models],
        "total": len(available_models),
        "excluded": excluded_count,
        "filtered": True
    }


@router.get("/models/all")
async def list_all_models(force_refresh: bool = Query(False)) -> dict[str, object]:
    """Liste ALLE Modelle (inkl. unavailable) - für Admin/Debug"""
    models = await registry.list_models(force_refresh=force_refresh)
    excluded = list(availability_service.get_excluded_models())
    
    return {
        "data": [model.to_dict() for model in models],
        "total": len(models),
        "excluded_models": excluded,
        "excluded_count": len(excluded)
    }
