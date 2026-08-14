import asyncio
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routes.mcp import _build_tool_result, handle_tools_call, handle_tools_list
from app.services.multi_search import (
    get_current_time,
    get_market_overview,
    get_stock_indices,
    list_timezones,
)


class TestMcpStructuredOutput(unittest.TestCase):
    def test_builder_preserves_legacy_text_and_structured_object(self):
        payload = {"ok": True, "count": 2}

        result = _build_tool_result(payload)

        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"], payload)
        self.assertEqual(json.loads(result["content"][0]["text"]), payload)

    def test_builder_wraps_non_object_for_generic_output_schema(self):
        result = _build_tool_result(["alpha", "beta"])

        self.assertEqual(result["structuredContent"], {"result": ["alpha", "beta"]})
        self.assertEqual(json.loads(result["content"][0]["text"]), ["alpha", "beta"])

    def test_current_time_uses_iana_timezone_database(self):
        result = asyncio.run(get_current_time("Europe/Berlin", "Berlin"))

        self.assertEqual(result["timezone"], "Europe/Berlin")
        self.assertEqual(result["location"], "Berlin")
        self.assertEqual(result["source"], "python_zoneinfo")
        self.assertRegex(result["date"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertRegex(result["time"], r"^\d{2}:\d{2}:\d{2}$")

    def test_current_time_rejects_unknown_timezone(self):
        with self.assertRaises(ValueError):
            asyncio.run(get_current_time("Invalid/Nowhere"))

    def test_list_timezones_filters_region(self):
        result = asyncio.run(list_timezones("Europe"))

        self.assertIn("Europe/Berlin", result["timezones"])
        self.assertTrue(all(zone.startswith("Europe/") for zone in result["timezones"]))
        self.assertEqual(result["count"], len(result["timezones"]))

    def test_restored_widget_functions_are_available(self):
        self.assertTrue(callable(get_stock_indices))
        self.assertTrue(callable(get_market_overview))
        self.assertTrue(callable(get_current_time))
        self.assertTrue(callable(list_timezones))

    def test_current_time_tool_call_has_structured_content(self):
        result = asyncio.run(
            handle_tools_call(
                {
                    "name": "current_time",
                    "arguments": {"timezone": "Europe/Berlin", "location": "Berlin"},
                }
            )
        )

        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"]["timezone"], "Europe/Berlin")
        self.assertEqual(
            json.loads(result["content"][0]["text"]),
            result["structuredContent"],
        )

    def test_advertised_output_schemas_are_objects(self):
        response = asyncio.run(handle_tools_list({}))

        self.assertGreater(response["count"], 100)
        self.assertTrue(
            all(tool.get("outputSchema", {}).get("type") == "object" for tool in response["tools"])
        )

    def test_debugger_reports_async_handler_correctly(self):
        from app.services.mcp_debugger import MCPDebugger

        async def async_handler(params):
            return params

        route_module = ModuleType("app.routes.mcp")
        route_module.MCP_HANDLERS = {"async_test": async_handler}
        remote_module = ModuleType("app.routes.mcp_remote")
        remote_module.TOOL_HANDLERS = {}

        with patch.dict(
            sys.modules,
            {
                "app.routes.mcp": route_module,
                "app.routes.mcp_remote": remote_module,
            },
        ):
            trace = asyncio.run(
                MCPDebugger().debug_mcp_request(
                    "tools/call", {"name": "async_test", "arguments": {}}
                )
            )

        self.assertEqual(trace["routing"]["status"], "found")
        self.assertIs(trace["handler_info"]["is_async"], True)
        self.assertTrue(trace["timestamp"].endswith("Z"))

    def test_user_group_chat_logs_returned_response(self):
        from app.mcp import handlers_user_chat
        from app.services import agent_chat_logger

        session_id = "uc-release-test"
        handlers_user_chat._USER_CHAT_SESSIONS.clear()
        handlers_user_chat._QUERY_SEM = None
        handlers_user_chat._USER_CHAT_SESSIONS[session_id] = {
            "session_id": session_id,
            "topic": "release",
            "model_ids": ["ollama/test-model"],
            "mode": "interactive",
            "history": [],
            "created_at": 1.0,
            "turn_count": 0,
        }

        async def fake_query(model_id, messages, timeout):
            return "model answer"

        logged = []
        fake_logger = SimpleNamespace(log_message=lambda **kwargs: logged.append(kwargs))
        with patch.object(handlers_user_chat, "_query_model", fake_query), patch.object(
            agent_chat_logger, "get_chat_logger", return_value=fake_logger
        ):
            result = asyncio.run(
                handlers_user_chat.handle_user_chat_tool(
                    "user_group_chat_reply",
                    {"session_id": session_id, "message": "hello"},
                )
            )

        self.assertEqual(result["responses"][0]["content"], "model answer")
        self.assertEqual(logged[0]["content"], "model answer")
        self.assertEqual(logged[0]["model"], "ollama/test-model")

    def test_admin_crawler_control_resolves_lazy_singletons(self):
        from app.routes.admin_crawler import CrawlerControlRequest, control_crawler
        from app.services import auto_publisher
        from app.services.crawler import user_crawler

        class FakeUserCrawler:
            _running = False

            async def start(self):
                self._running = True

            async def stop(self):
                self._running = False

        fake_user = FakeUserCrawler()
        with patch.object(user_crawler, "get_user_crawler", return_value=fake_user), patch.object(
            auto_publisher,
            "get_auto_publisher",
            return_value=SimpleNamespace(_task=None),
        ):
            result = asyncio.run(
                control_crawler(CrawlerControlRequest(action="start", instance="user"))
            )

        self.assertTrue(fake_user._running)
        self.assertTrue(result["results"]["user"]["changed"])

    def test_recent_crawler_jobs_uses_lazy_manager(self):
        from app.routes.admin_crawler import get_recent_jobs
        from app.services.crawler import manager

        job = SimpleNamespace(
            id="job-1",
            status="completed",
            priority="low",
            keywords=["release"],
            seeds=["https://example.test"],
            pages_crawled=1,
            max_pages=2,
            results=["result-1"],
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            requested_by="release-test",
            error=None,
        )

        class FakeManager:
            async def list_jobs(self):
                return [job]

        with patch.object(manager, "crawler_manager", FakeManager()):
            result = asyncio.run(get_recent_jobs(limit=20))

        self.assertEqual(result["jobs"][0]["id"], "job-1")

    def test_auto_publisher_stop_is_immediate(self):
        from app.services import auto_publisher

        settings = SimpleNamespace(
            wordpress_url="",
            wordpress_user="",
            wordpress_password="",
            wordpress_category_id=0,
            crawler_summary_model="ollama/test-model",
        )

        async def exercise():
            publisher = auto_publisher.AutoPublisher()
            await publisher.start()
            await asyncio.wait_for(publisher.stop(), timeout=0.25)
            return publisher

        with patch.object(auto_publisher, "get_settings", return_value=settings):
            publisher = asyncio.run(exercise())

        self.assertIsNone(publisher._task)

    def test_auto_publisher_does_not_deduplicate_failed_publish(self):
        from app.services import auto_publisher
        from app.services.crawler import manager

        settings = SimpleNamespace(
            wordpress_url="",
            wordpress_user="",
            wordpress_password="",
            wordpress_category_id=0,
            crawler_summary_model="ollama/test-model",
        )
        publisher = None
        results = {
            "first": SimpleNamespace(
                posted_at=None,
                content_hash="same-hash",
                title="first",
                score=0.9,
            ),
            "second": SimpleNamespace(
                posted_at=None,
                content_hash="same-hash",
                title="second",
                score=0.8,
            ),
        }

        class FakeManager:
            async def search(self, **kwargs):
                return [
                    {"id": "first", "score": 0.9},
                    {"id": "second", "score": 0.8},
                ]

            async def get_result(self, result_id):
                return results[result_id]

        calls = []

        async def fake_publish(result):
            calls.append(result.title)
            return result.title == "second"

        with patch.object(auto_publisher, "get_settings", return_value=settings):
            publisher = auto_publisher.AutoPublisher()
        with patch.object(manager, "crawler_manager", FakeManager()), patch.object(
            publisher,
            "_create_wordpress_post",
            fake_publish,
        ):
            asyncio.run(publisher._process_hourly())

        self.assertEqual(calls, ["first", "second"])

    def test_auto_publisher_updates_store_after_success(self):
        from app.services import auto_publisher
        from app.services.crawler import manager

        settings = SimpleNamespace(
            wordpress_url="https://wordpress.test",
            wordpress_user="user",
            wordpress_password="secret",
            wordpress_category_id=7,
            crawler_summary_model="ollama/test-model",
        )

        class FakeRegistry:
            async def get_model(self, model_id):
                return SimpleNamespace(id=model_id)

        class FakeChatService:
            async def stream_chat(self, *args, **kwargs):
                yield "generated article"

        class FakeWordPress:
            async def create_post(self, **kwargs):
                return {"id": 42}

        updated = []

        class FakeStore:
            async def update(self, result):
                updated.append(result)

        result = SimpleNamespace(
            title="Release article",
            url="https://example.test/source",
            summary="summary",
            content="content",
            posted_at=None,
            post_id=None,
        )

        with patch.object(auto_publisher, "get_settings", return_value=settings), patch.object(
            auto_publisher,
            "registry",
            FakeRegistry(),
        ), patch.object(
            auto_publisher,
            "chat_service",
            FakeChatService(),
        ), patch.object(
            auto_publisher,
            "wordpress_service",
            FakeWordPress(),
        ), patch.object(
            manager,
            "crawler_manager",
            SimpleNamespace(_store=FakeStore()),
        ):
            publisher = auto_publisher.AutoPublisher()
            published = asyncio.run(publisher._create_wordpress_post(result))

        self.assertTrue(published)
        self.assertEqual(result.post_id, 42)
        self.assertEqual(updated, [result])

    def test_specialist_write_keyword_keeps_both_capabilities(self):
        from app.mcp.specialists import SpecialistCapability, SpecialistRouter

        capabilities = SpecialistRouter().analyze_task("write")

        self.assertIn(SpecialistCapability.CODE_GENERATION, capabilities)
        self.assertIn(SpecialistCapability.TECHNICAL_WRITING, capabilities)

    def test_mesh_queue_command_forwards_priority(self):
        from app.routes import mesh

        captured = {}

        async def fake_queue(source, command, params, priority=2):
            captured["priority"] = priority
            return SimpleNamespace(to_dict=lambda: captured.copy())

        with patch.object(mesh, "queue_mcp_command", fake_queue):
            result = asyncio.run(
                mesh.handle_mesh_queue_command(
                    {
                        "source_agent": "release-agent",
                        "command": "status",
                        "params": {},
                        "priority": 0,
                    }
                )
            )

        self.assertEqual(result["command"]["priority"], 0)

    def test_compact_init_honors_max_token_budget(self):
        from app.services.init_service import compact_init

        result = compact_init.get_universal_init(max_tokens=16)

        self.assertLessEqual(len(result["compact_init"]), 64)
        self.assertLessEqual(result["token_count"], 16)

    def test_cli_agent_start_does_not_report_error_as_success(self):
        from app.routes import agents
        from app.services.tristar import agent_controller as controller_module

        class FakeController:
            async def start_agent(self, agent_id):
                return {"status": "error", "error": "executable unavailable"}

        with patch.object(controller_module, "agent_controller", FakeController()):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(agents.start_cli_agent("broken-agent"))

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(
            context.exception.detail["error"]["code"],
            "agent_start_failed",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
