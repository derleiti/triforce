import asyncio
import json

import pytest

from app.main import create_app
from app.routes.health import health_check


@pytest.fixture(scope="module")
def app_instance():
    return create_app()


def _get_endpoint(app, path: str):
    for route in app.router.routes:
        if getattr(route, "path", None) == path and "GET" in getattr(route, "methods", set()):
            return route.endpoint
    raise AssertionError(f"Endpoint for path {path} not found")


def test_health_check():
    response = asyncio.run(health_check())
    assert response.status_code == 200
    payload = json.loads(response.body.decode())
    assert payload["status"] == "ok"
    assert payload["ok"] is True
