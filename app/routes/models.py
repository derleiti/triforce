from __future__ import annotations

from fastapi import APIRouter, Query

from ..services.model_registry import registry

router = APIRouter(tags=["models"])


@router.get("/models")
async def list_models(force_refresh: bool = Query(False, description="Force-refresh the model registry")) -> dict[str, object]:
    models = await registry.list_models(force_refresh=force_refresh)
    return {"data": [model.to_dict() for model in models]}
