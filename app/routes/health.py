import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse, Response

router = APIRouter()

logger = logging.getLogger("ailinux.health")

HEALTH_RESPONSE = {"ok": True, "status": "ok"}


@router.get(
    "/health",
    tags=["Monitoring"],
    summary="Health check endpoint",
    include_in_schema=False,
)
@router.get(
    "/healthz",
    tags=["Monitoring"],
    summary="Kubernetes style health check endpoint",
    include_in_schema=False,
)
async def health_check():
    # Here you could add checks for database connection, external services, etc.
    # For now, a simple success response is sufficient.
    logger.info("Health probe received")
    return JSONResponse(content=HEALTH_RESPONSE, status_code=status.HTTP_200_OK)


@router.get(
    "/metrics",
    tags=["Monitoring"],
    summary="Prometheus metrics endpoint",
    include_in_schema=False,
)
async def prometheus_metrics():
    """
    Prometheus metrics endpoint for scraping.

    Provides metrics for:
    - Request count and latency
    - LLM calls and latency
    - Circuit breaker states
    - Memory entries
    - Active connections
    """
    # Import at runtime to avoid circular imports and ensure proper initialization
    try:
        from ..utils.metrics import get_metrics_response
        return get_metrics_response()
    except Exception as e:
        logger.warning(f"Failed to get metrics: {e}")
        return Response(
            content=f"# Metrics not available: {e}\n",
            media_type="text/plain"
        )
