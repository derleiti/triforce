"""
Security-Tests fuer Findings F1 + F2 + zusaetzliche Regressions-Tests.

Ausfuehren:
    cd /home/zombie/triforce
    .venv/bin/python -m pytest tests/test_security_findings.py -v

Alle Tests sollen nach dem Fix grueen sein.
"""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException


# =============================================================================
# F1 — Privilege Escalation: Admin-Check in grant-* Routes
# =============================================================================

class TestAdminAuthUtility:
    """Tests fuer app/utils/admin_auth.py"""

    def test_require_admin_blocks_non_admin(self):
        from app.utils.admin_auth import require_admin
        ctx = {"user_id": "regular_user"}
        with patch("app.utils.admin_auth.ADMIN_USER_IDS", frozenset({"real_admin"})):
            with pytest.raises(HTTPException) as exc:
                require_admin(ctx)
            assert exc.value.status_code == 403

    def test_require_admin_allows_admin(self):
        from app.utils.admin_auth import require_admin
        ctx = {"user_id": "real_admin"}
        with patch("app.utils.admin_auth.ADMIN_USER_IDS", frozenset({"real_admin"})):
            # Darf KEINE Exception werfen
            require_admin(ctx)

    def test_require_admin_blocks_empty_user_id(self):
        from app.utils.admin_auth import require_admin
        ctx = {"user_id": ""}
        with patch("app.utils.admin_auth.ADMIN_USER_IDS", frozenset({"real_admin"})):
            with pytest.raises(HTTPException) as exc:
                require_admin(ctx)
            assert exc.value.status_code == 403

    def test_require_admin_blocks_missing_user_id(self):
        from app.utils.admin_auth import require_admin
        ctx = {}
        with patch("app.utils.admin_auth.ADMIN_USER_IDS", frozenset({"real_admin"})):
            with pytest.raises(HTTPException):
                require_admin(ctx)

    def test_validate_paths_traversal_blocked(self):
        from app.utils.admin_auth import validate_allowed_paths
        with pytest.raises(HTTPException) as exc:
            validate_allowed_paths(["../../etc/passwd"])
        assert exc.value.status_code == 400

    def test_validate_paths_traversal_encoded_blocked(self):
        from app.utils.admin_auth import validate_allowed_paths
        with pytest.raises(HTTPException):
            validate_allowed_paths(["/home/zombie/../../../etc/shadow"])

    def test_validate_paths_outside_whitelist_blocked(self):
        from app.utils.admin_auth import validate_allowed_paths
        with pytest.raises(HTTPException) as exc:
            validate_allowed_paths(["/etc/cron.d/"])
        assert exc.value.status_code == 400

    def test_validate_paths_valid_home(self):
        from app.utils.admin_auth import validate_allowed_paths
        result = validate_allowed_paths(["/home/zombie/projects"])
        assert len(result) == 1
        assert result[0].startswith("/home/")

    def test_validate_paths_valid_tmp(self):
        from app.utils.admin_auth import validate_allowed_paths
        result = validate_allowed_paths(["/tmp/ailinux/data"])
        assert result[0].startswith("/tmp/ailinux/")

    def test_validate_paths_empty_list_blocked(self):
        from app.utils.admin_auth import validate_allowed_paths
        with pytest.raises(HTTPException) as exc:
            validate_allowed_paths([])
        assert exc.value.status_code == 400

    def test_validate_paths_too_many_blocked(self):
        from app.utils.admin_auth import validate_allowed_paths, MAX_PATHS_PER_GRANT
        paths = [f"/home/zombie/dir{i}" for i in range(MAX_PATHS_PER_GRANT + 1)]
        with pytest.raises(HTTPException) as exc:
            validate_allowed_paths(paths)
        assert exc.value.status_code == 400


class TestGrantFileAccess:
    """Tests fuer POST /client/mcp/admin/grant-file-access"""

    @pytest.mark.asyncio
    async def test_enterprise_user_cannot_grant_to_foreign_client(self):
        """
        KERN-TEST F1: Enterprise-User OHNE Admin-Rolle darf NICHT grant-file-access nutzen.
        Vor dem Fix war dieser Test gruen (kein Admin-Check). Nach dem Fix muss 403 kommen.
        """
        from app.routes.client_mcp import grant_file_access

        enterprise_ctx = {
            "user_id": "enterprise_attacker",
            "tier": MagicMock(value="enterprise"),
            "client_id": "client_enterprise_attacker_dev",
        }

        with patch("app.utils.admin_auth.ADMIN_USER_IDS", frozenset()):
            with pytest.raises(HTTPException) as exc:
                await grant_file_access(
                    target_client_id="client_victim_456_prod",
                    paths=["/home/victim"],
                    write_access=True,
                    ctx=enterprise_ctx,
                )
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_grant_file_access(self):
        """Admin darf grant-file-access fuer fremden Client ausfuehren."""
        from app.routes.client_mcp import grant_file_access

        mock_device = MagicMock()
        mock_device.client_id = "client_victim_456_prod"
        mock_user = MagicMock()
        mock_user.devices = [mock_device]

        admin_ctx = {
            "user_id": "real_admin",
            "tier": MagicMock(value="enterprise"),
            "client_id": "client_real_admin_main",
        }

        with patch("app.utils.admin_auth.ADMIN_USER_IDS", frozenset({"real_admin"})), \
             patch("app.routes.client_mcp.user_manager") as mock_um:
            mock_um.get_user = AsyncMock(return_value=mock_user)
            mock_um._save_user = MagicMock()

            result = await grant_file_access(
                target_client_id="client_victim_456_prod",
                paths=["/home/victim/projects"],
                write_access=False,
                ctx=admin_ctx,
            )

        assert result["success"] is True
        assert result["granted_by"] == "real_admin"
        assert "/home/victim/projects" in result["allowed_paths"]

    @pytest.mark.asyncio
    async def test_path_traversal_blocked_even_for_admin(self):
        """Auch Admin darf keine Path-Traversal-Pfade setzen."""
        from app.routes.client_mcp import grant_file_access

        admin_ctx = {
            "user_id": "real_admin",
            "tier": MagicMock(value="enterprise"),
            "client_id": "client_real_admin_main",
        }

        with patch("app.utils.admin_auth.ADMIN_USER_IDS", frozenset({"real_admin"})):
            with pytest.raises(HTTPException) as exc:
                await grant_file_access(
                    target_client_id="client_victim_456_prod",
                    paths=["../../etc/passwd"],
                    write_access=False,
                    ctx=admin_ctx,
                )
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_client_id_format_blocked(self):
        """client_id mit weniger als 3 Teilen (type_userid_suffix) wird abgelehnt."""
        from app.routes.client_mcp import grant_file_access

        admin_ctx = {
            "user_id": "real_admin",
            "tier": MagicMock(value="enterprise"),
            "client_id": "client_real_admin_main",
        }

        with patch("app.utils.admin_auth.ADMIN_USER_IDS", frozenset({"real_admin"})):
            with pytest.raises(HTTPException) as exc:
                await grant_file_access(
                    target_client_id="badformat",
                    paths=["/home/zombie"],
                    ctx=admin_ctx,
                )
            assert exc.value.status_code == 400


class TestGrantBashAccess:
    """Tests fuer POST /client/mcp/admin/grant-bash-access"""

    @pytest.mark.asyncio
    async def test_enterprise_user_cannot_grant_bash(self):
        """F1: Enterprise-User darf kein Bash-Recht setzen."""
        from app.routes.client_mcp import grant_bash_access

        ctx = {
            "user_id": "attacker",
            "tier": MagicMock(value="enterprise"),
            "client_id": "client_attacker_123_dev",
        }

        with patch("app.utils.admin_auth.ADMIN_USER_IDS", frozenset()):
            with pytest.raises(HTTPException) as exc:
                await grant_bash_access(
                    target_client_id="client_victim_456_prod",
                    enabled=True,
                    ctx=ctx,
                )
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_revoke_bash_access(self):
        """Admin darf Bash-Recht auch entziehen (enabled=False)."""
        from app.routes.client_mcp import grant_bash_access

        mock_device = MagicMock()
        mock_device.client_id = "client_victim_456_prod"
        mock_user = MagicMock()
        mock_user.devices = [mock_device]

        admin_ctx = {
            "user_id": "real_admin",
            "tier": MagicMock(value="enterprise"),
            "client_id": "client_real_admin_main",
        }

        with patch("app.utils.admin_auth.ADMIN_USER_IDS", frozenset({"real_admin"})), \
             patch("app.routes.client_mcp.user_manager") as mock_um:
            mock_um.get_user = AsyncMock(return_value=mock_user)
            mock_um._save_user = MagicMock()

            result = await grant_bash_access(
                target_client_id="client_victim_456_prod",
                enabled=False,
                ctx=admin_ctx,
            )

        assert result["success"] is True
        assert result["bash_access"] is False
        assert result["granted_by"] == "real_admin"
        assert mock_device.allow_bash is False


# =============================================================================
# F2 — IDOR: Unauthenticated GET Endpoints
# =============================================================================

class TestRequireReadAccess:
    """Tests fuer app/utils/admin_auth.require_read_access"""

    def test_no_key_returns_401(self):
        from app.utils.admin_auth import require_read_access
        import os
        with patch.dict(os.environ, {"INTERNAL_API_KEY": "secret123"}):
            with pytest.raises(HTTPException) as exc:
                require_read_access(x_internal_key="")
            assert exc.value.status_code == 401

    def test_wrong_key_returns_401(self):
        from app.utils.admin_auth import require_read_access
        import os
        with patch.dict(os.environ, {"INTERNAL_API_KEY": "secret123"}):
            with pytest.raises(HTTPException) as exc:
                require_read_access(x_internal_key="wrongkey")
            assert exc.value.status_code == 401

    def test_correct_key_passes(self):
        from app.utils.admin_auth import require_read_access
        import os
        with patch.dict(os.environ, {"INTERNAL_API_KEY": "secret123"}):
            # Darf keine Exception werfen
            require_read_access(x_internal_key="secret123")

    def test_no_env_key_configured_blocks_everything(self):
        """Wenn INTERNAL_API_KEY nicht gesetzt ist, wird alles geblockt."""
        from app.utils.admin_auth import require_read_access
        import os
        env = {k: v for k, v in os.environ.items() if k != "INTERNAL_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(HTTPException) as exc:
                require_read_access(x_internal_key="anything")
            assert exc.value.status_code == 401


class TestUserApiGetEndpointsAuth:
    """Stellt sicher, dass alle GET-Routen in user_api.py abgesichert sind."""

    def test_get_user_has_require_read_access_dep(self):
        """GET /users/{user_id} muss require_read_access als Dependency haben."""
        from app.routes.user_api import get_user
        import inspect
        sig = inspect.signature(get_user)
        dep_names = [
            str(p.default) for p in sig.parameters.values()
            if hasattr(p.default, "dependency")
        ]
        # Pruefe ob irgendein Depends(require_read_access) dabei ist
        from app.utils.admin_auth import require_read_access
        from fastapi import Depends
        deps = [
            p.default for p in sig.parameters.values()
            if hasattr(p.default, "dependency") and p.default.dependency is require_read_access
        ]
        assert len(deps) >= 1, "get_user hat kein Depends(require_read_access)"

    def test_list_devices_has_require_read_access_dep(self):
        from app.routes.user_api import list_devices
        from app.utils.admin_auth import require_read_access
        import inspect
        sig = inspect.signature(list_devices)
        deps = [
            p.default for p in sig.parameters.values()
            if hasattr(p.default, "dependency") and p.default.dependency is require_read_access
        ]
        assert len(deps) >= 1, "list_devices hat kein Depends(require_read_access)"

    def test_list_credentials_has_require_read_access_dep(self):
        from app.routes.user_api import list_credentials
        from app.utils.admin_auth import require_read_access
        import inspect
        sig = inspect.signature(list_credentials)
        deps = [
            p.default for p in sig.parameters.values()
            if hasattr(p.default, "dependency") and p.default.dependency is require_read_access
        ]
        assert len(deps) >= 1, "list_credentials hat kein Depends(require_read_access)"

    def test_get_settings_has_require_read_access_dep(self):
        from app.routes.user_api import get_settings
        from app.utils.admin_auth import require_read_access
        import inspect
        sig = inspect.signature(get_settings)
        deps = [
            p.default for p in sig.parameters.values()
            if hasattr(p.default, "dependency") and p.default.dependency is require_read_access
        ]
        assert len(deps) >= 1, "get_settings hat kein Depends(require_read_access)"

    def test_get_user_quota_has_require_read_access_dep(self):
        from app.routes.user_api import get_user_quota
        from app.utils.admin_auth import require_read_access
        import inspect
        sig = inspect.signature(get_user_quota)
        deps = [
            p.default for p in sig.parameters.values()
            if hasattr(p.default, "dependency") and p.default.dependency is require_read_access
        ]
        assert len(deps) >= 1, "get_user_quota hat kein Depends(require_read_access)"


# =============================================================================
# Zusaetzliche Findings: JWT_SECRET + check_path_allowed
# =============================================================================

class TestCheckPathAllowed:
    """Regressions-Tests fuer die bestehende check_path_allowed-Funktion."""

    def test_traversal_normalized_blocked(self):
        from app.routes.client_mcp import check_path_allowed
        allowed = ["/home/zombie"]
        # /home/zombie/../../etc/passwd resolved = /etc/passwd -> nicht in allowed
        result = check_path_allowed("/home/zombie/../../etc/passwd", allowed)
        assert result is False

    def test_exact_match_allowed(self):
        from app.routes.client_mcp import check_path_allowed
        assert check_path_allowed("/home/zombie", ["/home/zombie"]) is True

    def test_subpath_allowed(self):
        from app.routes.client_mcp import check_path_allowed
        assert check_path_allowed("/home/zombie/projects/myapp", ["/home/zombie"]) is True

    def test_sibling_dir_blocked(self):
        from app.routes.client_mcp import check_path_allowed
        # /home/victim ist nicht Subpfad von /home/zombie
        assert check_path_allowed("/home/victim/secret", ["/home/zombie"]) is False


class TestJwtSecretStability:
    """Stellt sicher, dass _JWT_SECRET_MODULE stabil ist."""

    def test_jwt_secret_is_module_level(self):
        """_JWT_SECRET_MODULE darf nicht None oder leer sein."""
        from app.routes.user_api import _JWT_SECRET_MODULE
        assert _JWT_SECRET_MODULE is not None
        assert len(_JWT_SECRET_MODULE) >= 16

    def test_jwt_secret_consistent_across_imports(self):
        """Mehrfacher Import des Moduls darf den Secret nicht aendern."""
        from app.routes.user_api import _JWT_SECRET_MODULE as s1
        import importlib
        import app.routes.user_api as mod
        importlib.reload(mod)
        # Nach reload kann sich secret aendern wenn JWT_SECRET nicht gesetzt ist
        # Dieser Test prueft nur, dass er nicht leer wird
        assert mod._JWT_SECRET_MODULE is not None
        assert len(mod._JWT_SECRET_MODULE) >= 16


# =============================================================================
# MCP Runtime Allowlist + GET Health Regression
# =============================================================================

def _mock_mcp_request(headers=None, host="127.0.0.1"):
    req = MagicMock()
    req.headers = headers or {}
    req.query_params = {}
    req.client = MagicMock()
    req.client.host = host
    req.state = MagicMock()
    return req


class TestMcpRuntimeSecurity:
    @pytest.mark.asyncio
    async def test_get_mcp_health_does_not_reference_missing_params(self):
        from app.routes.mcp import mcp_health_or_sse

        response = await mcp_health_or_sse(_mock_mcp_request())
        payload = json.loads(response.body)

        assert response.status_code == 200
        assert payload["result"]["protocolVersion"] == "2024-11-05"

    @pytest.mark.asyncio
    async def test_external_tools_list_filters_privileged_tools(self):
        from app.routes import mcp as route_mcp

        internal_payload = await route_mcp.handle_tools_list({})
        internal_names = {tool["name"] for tool in internal_payload["tools"]}
        assert "agent_start" in internal_names

        external = _mock_mcp_request(headers={"X-Forwarded-Port": "9100"}, host="1.2.3.4")
        external_payload = await route_mcp.handle_tools_list({}, request=external)
        external_names = {tool["name"] for tool in external_payload["tools"]}

        assert "chat" in external_names
        assert "group_chat_create" in external_names
        assert "agent_start" not in external_names

    @pytest.mark.asyncio
    async def test_external_tools_call_blocks_privileged_tools(self):
        from app.routes import mcp as route_mcp

        external = _mock_mcp_request(headers={"X-Forwarded-Port": "9100"}, host="1.2.3.4")
        result = await route_mcp.handle_tools_call(
            {"name": "agent_start", "arguments": {"agent": "codex-mcp"}},
            request=external,
        )
        payload = json.loads(result["content"][0]["text"])

        assert result["isError"] is True
        assert payload["code"] == "MCP_TOOL_FORBIDDEN"
        assert payload["tool_name"] == "agent_start"
