import asyncio
import json
import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
