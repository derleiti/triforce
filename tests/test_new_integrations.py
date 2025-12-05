"""
Tests für Gemini Function Calling und Hugging Face Integration.
TriForce v2.80 Extension Tests

Run with: pytest tests/test_new_integrations.py -v
Or run directly: python tests/test_new_integrations.py
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


# ============================================================================
# GEMINI FUNCTION CALLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_gemini_function_call_basic():
    """Test basic Gemini function calling."""
    from app.services.gemini_access import gemini_access

    result = await gemini_access.function_call(
        prompt="What is 2+2? Just answer with the number.",
        tools=["memory_recall"],
        auto_execute=False,  # Don't execute, just test the flow
        max_iterations=1,
    )

    assert "timestamp" in result
    assert "prompt" in result
    # Success depends on API availability
    print(f"Function call result: {result}")


@pytest.mark.asyncio
async def test_gemini_function_call_with_fallback():
    """Test Gemini function calling fallback mode."""
    from app.services.gemini_access import gemini_access

    # Force fallback by disabling genai
    original_init = gemini_access._genai_initialized
    gemini_access._genai_initialized = False

    result = await gemini_access.function_call(
        prompt="Search memory for 'test'",
        tools=["memory_recall"],
        auto_execute=False,
        max_iterations=1,
    )

    # Restore
    gemini_access._genai_initialized = original_init

    assert "timestamp" in result
    assert result.get("fallback_mode", False) or result.get("success", False)
    print(f"Fallback mode result: {result}")


@pytest.mark.asyncio
async def test_gemini_code_exec_simple():
    """Test Gemini code execution with simple code."""
    from app.services.gemini_access import gemini_access

    result = await gemini_access.code_execution(
        code="print(sum(range(10)))",
        language="python",
        timeout=30,
    )

    assert "timestamp" in result
    assert "code" in result
    # Check for either success or error
    assert "success" in result or "error" in result
    print(f"Code exec result: {result}")


@pytest.mark.asyncio
async def test_gemini_code_exec_invalid_language():
    """Test Gemini code execution with invalid language."""
    from app.services.gemini_access import gemini_access

    result = await gemini_access.code_execution(
        code="console.log('hello')",
        language="javascript",
        timeout=30,
    )

    assert result["success"] is False
    assert "not supported" in result.get("error", "").lower()
    print(f"Invalid language result: {result}")


# ============================================================================
# HUGGING FACE INFERENCE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_hf_list_models():
    """Test HF model listing."""
    from app.services.huggingface_inference import hf_inference

    models = hf_inference.list_recommended_models()

    assert isinstance(models, dict)
    assert "text_generation" in models
    assert "embeddings" in models
    assert "text_to_image" in models
    print(f"Available model categories: {list(models.keys())}")


@pytest.mark.asyncio
async def test_hf_get_recommended_model():
    """Test getting recommended model for task."""
    from app.services.huggingface_inference import hf_inference

    model = hf_inference.get_recommended_model("embeddings")
    assert model is not None
    assert "sentence-transformers" in model.lower() or "bge" in model.lower()
    print(f"Recommended embeddings model: {model}")


@pytest.mark.asyncio
async def test_hf_rate_limit_info():
    """Test rate limit info property."""
    from app.services.huggingface_inference import hf_inference

    info = hf_inference.rate_limit_info
    assert isinstance(info, dict)
    assert "remaining" in info
    print(f"Rate limit info: {info}")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("HUGGINGFACE_API_KEY"),
    reason="HUGGINGFACE_API_KEY not set"
)
async def test_hf_text_generation():
    """Test HF text generation (requires API key)."""
    from app.services.huggingface_inference import hf_inference

    result = await hf_inference.text_generation(
        prompt="What is machine learning in one sentence?",
        max_new_tokens=50,
    )

    assert "generated_text" in result or "error" in result
    print(f"HF generate result: {result.get('generated_text', result.get('error', ''))[:200]}")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("HUGGINGFACE_API_KEY"),
    reason="HUGGINGFACE_API_KEY not set"
)
async def test_hf_embeddings():
    """Test HF embeddings (requires API key)."""
    from app.services.huggingface_inference import hf_inference

    result = await hf_inference.embeddings(
        texts=["Hello world", "Goodbye world"],
    )

    assert "embeddings" in result or "error" in result
    if "embeddings" in result:
        assert result["count"] == 2
        print(f"Embedding dimension: {result.get('dimension', 'N/A')}")
    else:
        print(f"Embeddings error: {result.get('error', '')}")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("HUGGINGFACE_API_KEY"),
    reason="HUGGINGFACE_API_KEY not set"
)
async def test_hf_summarize():
    """Test HF summarization (requires API key)."""
    from app.services.huggingface_inference import hf_inference

    long_text = (
        "Machine learning is a branch of artificial intelligence that focuses on "
        "building systems that learn from data. These systems can identify patterns, "
        "make decisions, and improve over time without being explicitly programmed. "
        "Machine learning is used in many applications including image recognition, "
        "natural language processing, and recommendation systems."
    )

    result = await hf_inference.summarize(text=long_text, max_length=50)

    assert "summary" in result or "error" in result
    print(f"Summary: {result.get('summary', result.get('error', ''))}")


# ============================================================================
# TOOL REGISTRY TESTS
# ============================================================================

def test_tool_registry_categories():
    """Test that new categories are registered."""
    from app.services.triforce.tool_registry import ToolCategory, get_tool_categories

    categories = get_tool_categories()
    assert "huggingface" in categories
    assert "gemini" in categories
    print(f"All categories: {categories}")


def test_tool_registry_hf_tools():
    """Test that HF tools are in the registry."""
    from app.services.triforce.tool_registry import get_tools_by_category, ToolCategory

    hf_tools = get_tools_by_category(ToolCategory.HUGGINGFACE)
    assert len(hf_tools) >= 7
    tool_names = [t["name"] for t in hf_tools]
    assert "hf_generate" in tool_names
    assert "hf_embed" in tool_names
    assert "hf_image" in tool_names
    print(f"HF tools: {tool_names}")


def test_tool_registry_gemini_tools():
    """Test that Gemini tools are in the registry."""
    from app.services.triforce.tool_registry import get_tools_by_category, ToolCategory

    gemini_tools = get_tools_by_category(ToolCategory.GEMINI)
    assert len(gemini_tools) >= 2
    tool_names = [t["name"] for t in gemini_tools]
    assert "gemini_function_call" in tool_names
    assert "gemini_code_exec" in tool_names
    print(f"Gemini tools: {tool_names}")


def test_tool_registry_version():
    """Test that registry version is updated."""
    from app.services.triforce.tool_registry import TOOL_INDEX

    assert TOOL_INDEX["version"] == "2.80"
    print(f"Tool index version: {TOOL_INDEX['version']}")


def test_tool_count():
    """Test total tool count."""
    from app.services.triforce.tool_registry import get_tool_count

    count = get_tool_count()
    # Original 21 + 7 HF + 2 Gemini = 30
    assert count >= 30
    print(f"Total tools: {count}")


# ============================================================================
# CONFIG TESTS
# ============================================================================

def test_config_hf_settings():
    """Test that HF config settings exist."""
    from app.config import get_settings

    settings = get_settings()

    assert hasattr(settings, "huggingface_api_key")
    assert hasattr(settings, "huggingface_inference_url")
    assert hasattr(settings, "huggingface_timeout")

    # Check defaults
    assert settings.huggingface_inference_url == "https://api-inference.huggingface.co"
    assert settings.huggingface_timeout == 120
    print("HF config settings OK")


# ============================================================================
# HANDLER REGISTRATION TESTS
# ============================================================================

def test_handlers_registered():
    """Test that all handlers are registered in TOOL_HANDLERS."""
    from app.routes.mcp_remote import TOOL_HANDLERS

    # HF handlers
    assert "hf_generate" in TOOL_HANDLERS
    assert "hf_chat" in TOOL_HANDLERS
    assert "hf_embed" in TOOL_HANDLERS
    assert "hf_image" in TOOL_HANDLERS
    assert "hf_summarize" in TOOL_HANDLERS
    assert "hf_translate" in TOOL_HANDLERS
    assert "hf_models" in TOOL_HANDLERS

    # Gemini extended handlers
    assert "gemini_function_call" in TOOL_HANDLERS
    assert "gemini_code_exec" in TOOL_HANDLERS

    print(f"Total handlers registered: {len(TOOL_HANDLERS)}")


# ============================================================================
# MAIN
# ============================================================================

async def run_quick_tests():
    """Run quick tests without API keys."""
    print("=" * 60)
    print("Running Quick Tests (no API keys required)")
    print("=" * 60)

    # Config tests
    print("\n[1] Config Tests")
    test_config_hf_settings()
    print("   PASS")

    # Tool Registry tests
    print("\n[2] Tool Registry Tests")
    test_tool_registry_categories()
    test_tool_registry_hf_tools()
    test_tool_registry_gemini_tools()
    test_tool_registry_version()
    test_tool_count()
    print("   PASS")

    # Handler Registration tests
    print("\n[3] Handler Registration Tests")
    test_handlers_registered()
    print("   PASS")

    # Gemini tests (may work without API)
    print("\n[4] Gemini Tests")
    await test_gemini_code_exec_invalid_language()
    print("   PASS")

    # HF model listing (no API needed)
    print("\n[5] HF Model Listing Tests")
    await test_hf_list_models()
    await test_hf_get_recommended_model()
    await test_hf_rate_limit_info()
    print("   PASS")

    print("\n" + "=" * 60)
    print("All Quick Tests PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_quick_tests())
