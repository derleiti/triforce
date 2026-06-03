from pathlib import Path

import pytest
from fastapi.responses import JSONResponse

from app.routes import nova_operator


@pytest.mark.asyncio
async def test_operator_context_is_read_only_and_masks_secrets(monkeypatch):
    async def fake_models(force_refresh: bool):
        assert force_refresh is False
        return {
            "total": 2,
            "available_total": 2,
            "unavailable_total": 0,
            "providers": {"ollama": 1, "anthropic": 1},
            "capabilities": {"chat": 2},
            "roles": {"assistant": 2},
            "sample_unavailable": [],
        }

    async def fake_agents():
        return {
            "count": 1,
            "status_counts": {"stopped": 1},
            "agents": [{"id": "claude-mcp", "status": "stopped", "running": False, "pid": None, "model": None}],
        }

    monkeypatch.setattr(nova_operator, "_model_summary", fake_models)
    monkeypatch.setattr(nova_operator, "_agent_summary", fake_agents)
    monkeypatch.setattr(nova_operator, "_tool_summary", lambda: {"agent_tools_total": 0, "categories": {}})
    monkeypatch.setattr(
        nova_operator,
        "_safe_settings_summary",
        lambda: {
            "providers_configured": ["anthropic"],
            "providers_count": 1,
            "redis_configured": True,
            "cors_configured": True,
            "secrets_exposed": False,
        },
    )
    monkeypatch.setattr(
        nova_operator,
        "_filesystem_summary",
        lambda: {
            "nova_ai_frontend": {"exists": True},
            "ailinux_rss_reader": {"exists": True},
            "nova_theme": {"exists": True},
        },
    )

    response = await nova_operator.operator_context(False)

    assert isinstance(response, JSONResponse)
    body = response.body.decode()
    assert response.status_code == 200
    assert "sk-" not in body.lower()
    assert "AIza" not in body
    assert "write_files" in body
    assert "inspect_context" in body
    assert "CLI agents are present" in body


def test_project_root_resolution_points_to_repo():
    assert isinstance(nova_operator.PROJECT_ROOT, Path)
    assert (nova_operator.PROJECT_ROOT / "app").exists()
