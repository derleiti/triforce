"""Dependency-light contract tests for the external ai-coder MCP profile."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest


_MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "utils" / "mcp_security.py"
_SPEC = importlib.util.spec_from_file_location("aicoder_mcp_security_contract", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_SECURITY = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_SECURITY)

_NORMALIZER_PATH = Path(__file__).resolve().parents[1] / "app" / "utils" / "tool_normalizer.py"
_NORMALIZER_SPEC = importlib.util.spec_from_file_location(
    "aicoder_tool_normalizer_contract", _NORMALIZER_PATH,
)
assert _NORMALIZER_SPEC is not None and _NORMALIZER_SPEC.loader is not None
_NORMALIZER = importlib.util.module_from_spec(_NORMALIZER_SPEC)
_NORMALIZER_SPEC.loader.exec_module(_NORMALIZER)

AI_CODER_TOOL_ALLOWLIST = _SECURITY.AI_CODER_TOOL_ALLOWLIST
filter_tools_for_external = _SECURITY.filter_tools_for_external
is_tool_allowed = _SECURITY.is_tool_allowed


EXPECTED_AI_CODER_TOOLS = {
    "code_read", "code_search", "code_tree",
    "dev_analyze", "dev_debug", "dev_lint", "dev_links",
    "dev_refactor", "dev_summarize",
    "doc_read", "doc_search",
    "health", "search", "crawl",
    "memory_search", "memory_store",
    "models", "specialist", "prompts", "swarm_broadcast",
}


class FakeRequest:
    def __init__(self, profile="ai-coder"):
        self.headers = {
            "X-Client-Profile": profile,
            "X-Forwarded-For": "203.0.113.20",
        }
        self.client = SimpleNamespace(host="203.0.113.20")
        self.state = SimpleNamespace()


class AiCoderMcpContractTests(unittest.TestCase):
    def test_ai_coder_contract_is_explicit_and_stable(self):
        self.assertEqual(AI_CODER_TOOL_ALLOWLIST, EXPECTED_AI_CODER_TOOLS)

    def test_ai_coder_catalog_is_exact_and_default_deny(self):
        catalog = [{"name": name} for name in EXPECTED_AI_CODER_TOOLS]
        catalog.extend([
            {"name": "shell"}, {"name": "service_status"}, {"name": "memory_clear"},
        ])

        visible = filter_tools_for_external(catalog, request=FakeRequest())

        self.assertEqual({tool["name"] for tool in visible}, EXPECTED_AI_CODER_TOOLS)

    def test_ai_coder_calls_match_catalog_and_never_gain_ops_tools(self):
        request = FakeRequest()
        self.assertTrue(all(is_tool_allowed(name, request) for name in EXPECTED_AI_CODER_TOOLS))
        for forbidden in (
            "shell", "task_runner", "admin_users", "service_status", "memory_clear", "debug",
        ):
            with self.subTest(tool=forbidden):
                self.assertFalse(is_tool_allowed(forbidden, request))

    def test_canonical_names_survive_legacy_alias_normalization(self):
        request = FakeRequest(profile="")
        # tools/call resolves ask_specialist -> specialist and crawl_url -> crawl
        # before invoking this policy.
        self.assertTrue(is_tool_allowed("specialist", request))
        self.assertTrue(is_tool_allowed("crawl", request))

    def test_backend_readonly_metadata_matches_client_approval_semantics(self):
        readonly = EXPECTED_AI_CODER_TOOLS - {"crawl", "memory_store", "swarm_broadcast"}
        self.assertTrue(all(_NORMALIZER.is_readonly_tool(name) for name in readonly))
        self.assertFalse(_NORMALIZER.is_readonly_tool("crawl"))
        self.assertFalse(_NORMALIZER.is_readonly_tool("memory_store"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
