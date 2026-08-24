from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services import remote_coding_agent as service


class FakeTier:
    value = "pro"


class FakeConnection:
    def __init__(self, *, writes: bool = False):
        self.client_id = "client-1"
        self.user_id = "user@example.test"
        self.tier = FakeTier()
        self.mode = "full"
        self.client_info = {
            "client": "aicoder",
            "hostname": "workstation",
            "workspace": "/work/repo",
            "remote_profile": "write-preview" if writes else "read-only-light",
        }
        tools = set(service.REMOTE_READ_TOOLS) | service.REMOTE_CONTROL_TOOLS
        if writes:
            tools |= service.REMOTE_WRITE_TOOLS
        self.supported_tools = sorted(tools)
        self.send_tool_call = AsyncMock(return_value={
            "content": [{"type": "text", "text": "hello"}],
            "isError": False,
        })


def test_lists_only_full_aicoder_nodes(monkeypatch):
    good = FakeConnection()
    other = FakeConnection()
    other.client_id = "other"
    other.client_info = {"client": "something-else"}
    monkeypatch.setattr(service, "CONNECTED_CLIENTS", {"client-1": good, "alias": good, "other": other})
    rows = service.list_remote_coding_nodes()
    assert len(rows) == 1
    assert rows[0].client_id == "client-1"
    assert rows[0].workspace == "/work/repo"
    assert rows[0].profile == "read-only-light"
    assert set(rows[0].supported_tools) == service.REMOTE_READ_TOOLS | service.REMOTE_CONTROL_TOOLS


@pytest.mark.asyncio
async def test_remote_tool_proxy_requires_explicit_advertisement():
    conn = FakeConnection()
    text = await service._call_client_tool(conn, "client_file_read", {"path": "README.md"})
    assert text == "hello"
    conn.send_tool_call.assert_awaited_once()

    with pytest.raises(LookupError):
        await service._call_client_tool(
            conn,
            "client_file_edit",
            {"path": "x", "operation": "create", "content": "x"},
        )
    with pytest.raises(PermissionError):
        await service._call_client_tool(conn, "client_shell", {"command": "id"})


@pytest.mark.asyncio
async def test_remote_write_error_is_returned_as_untrusted_tool_error():
    conn = FakeConnection(writes=True)
    conn.send_tool_call = AsyncMock(return_value={
        "content": [{"type": "text", "text": "exact match failed"}],
        "isError": True,
    })
    text = await service._call_client_tool(
        conn,
        "client_file_edit",
        {"path": "x.py", "operation": "replace", "old_text": "a", "new_text": "b"},
    )
    assert text == "REMOTE TOOL ERROR: exact match failed"


def test_custom_tool_set_matches_only_advertised_tools():
    read_conn = FakeConnection()
    read_tools = service._build_remote_tools(read_conn)
    assert {tool.__name__ for tool in read_tools} == service.REMOTE_READ_TOOLS

    write_conn = FakeConnection(writes=True)
    write_tools = service._build_remote_tools(write_conn)
    assert {tool.__name__ for tool in write_tools} == service.REMOTE_MODEL_TOOLS
    assert "client_run_state" not in {tool.__name__ for tool in write_tools}

    empty = FakeConnection()
    empty.supported_tools = []
    assert service._build_remote_tools(empty) == []


@pytest.mark.asyncio
async def test_file_edit_wrapper_forwards_only_preview_operations():
    conn = FakeConnection(writes=True)
    tools = {tool.__name__: tool for tool in service._build_remote_tools(conn)}
    await tools["client_file_edit"](
        "src/x.py",
        "replace",
        old_text="before",
        new_text="after",
    )
    conn.send_tool_call.assert_awaited_once_with(
        "client_file_edit",
        {
            "path": "src/x.py",
            "operation": "replace",
            "old_text": "before",
            "new_text": "after",
        },
        timeout=60.0,
    )


def test_antigravity_sdk_is_isolated_from_core_requirements():
    core = open("requirements.txt", encoding="utf-8").read()
    isolated = open("requirements-antigravity.txt", encoding="utf-8").read()
    assert not any(line.strip().startswith("google-antigravity") for line in core.splitlines())
    assert "google-antigravity==0.1.13" in isolated


def test_antigravity_base_url_accepts_openai_v1_form():
    assert service.normalize_antigravity_model_base_url("http://127.0.0.1:9000/v1") == "http://127.0.0.1:9000"
    assert service.normalize_antigravity_model_base_url("http://127.0.0.1:9000/v1/") == "http://127.0.0.1:9000"
    assert service.normalize_antigravity_model_base_url("http://127.0.0.1:9000") == "http://127.0.0.1:9000"


@pytest.mark.asyncio
async def test_run_id_is_forwarded_and_control_tool_stays_internal(monkeypatch):
    conn = FakeConnection(writes=True)
    monkeypatch.setattr(service, "CONNECTED_CLIENTS", {"client-1": conn})
    worker = AsyncMock(return_value={"response": "DONE: ok", "usage": None})
    monkeypatch.setattr(service, "_run_antigravity_worker", worker)

    result = await service.run_remote_coding_agent(
        client_id="client-1",
        task="change safely",
        model="test/model",
        run_id="remote-resume-1",
    )

    assert result["run_id"] == "remote-resume-1"
    worker.assert_awaited_once()
    assert worker.await_args.kwargs["run_id"] == "remote-resume-1"


def test_invalid_run_id_is_rejected_before_worker(monkeypatch):
    conn = FakeConnection(writes=True)
    monkeypatch.setattr(service, "CONNECTED_CLIENTS", {"client-1": conn})
    with pytest.raises(ValueError, match="invalid run_id"):
        import asyncio
        asyncio.run(service.run_remote_coding_agent(
            client_id="client-1",
            task="x",
            run_id="bad/run/id",
        ))
