from __future__ import annotations

import logging
import re
from typing import Tuple

from . import chat as chat_service
from .model_registry import ModelInfo

logger = logging.getLogger("ailinux.text_analysis")

# Limit the text we hand to the model to avoid huge prompts
MAX_ANALYSIS_CHARACTERS = 20000

SUMMARY_SYSTEM_PROMPT = (
    "You are a concise text analyst. Given a user-provided document, return two short sections "
    "in English: (1) Summary – 3-6 bullet points or a tight paragraph capturing the core ideas; "
    "(2) Model comment – one or two sentences noting tone, risks, or missing context. "
    "Stay under 180 words total and never echo the full source text."
)

SECTION_SPLIT_PATTERN = re.compile(
    r"(model\s+comment|commentary|model\s+note)\s*[:\-]",
    re.IGNORECASE,
)


def _split_sections(text: str) -> Tuple[str, str]:
    """
    Try to split the model response into summary + model comment sections while
    keeping the output resilient if the model does not follow the requested format.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return "", ""

    match = SECTION_SPLIT_PATTERN.search(cleaned)
    if not match:
        return cleaned, ""

    summary = cleaned[: match.start()].strip()
    comment = cleaned[match.end() :].strip()

    def _strip_label(value: str) -> str:
        return re.sub(
            r"^(summary|model\s+comment|commentary|model\s+note)\s*[:\-]\s*",
            "",
            value,
            flags=re.IGNORECASE,
        ).strip()

    return _strip_label(summary), _strip_label(comment)


async def analyze_text(
    model: ModelInfo,
    model_id: str,
    text: str,
    *,
    truncated: bool,
    original_characters: int,
) -> dict[str, str | bool | int]:
    if not text or not text.strip():
        from ..utils.errors import api_error

        raise api_error("Text payload is empty", status_code=422, code="empty_text")

    prompt_notes = [
        f"The provided text is {len(text)} characters long.",
        "Return the result in English.",
    ]
    if truncated:
        prompt_notes.append("The text was truncated to protect the service from oversized uploads.")

    user_prompt = "\\n".join(prompt_notes) + "\\n\\n" + text.strip()

    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": user_prompt,
        },
    ]

    logger.info(
        "text_analysis_request",
        extra={
            "model_id": model_id,
            "original_characters": original_characters,
            "analyzed_characters": len(text),
            "truncated": truncated,
        },
    )

    chunks: list[str] = []
    async for chunk in chat_service.stream_chat(
        model,
        model_id,
        messages,
        stream=True,
        temperature=0.35,
    ):
        chunks.append(chunk)

    combined = "".join(chunks).strip()
    summary, model_comment = _split_sections(combined)

    return {
        "summary": summary or combined,
        "model_comment": model_comment,
        "truncated": truncated,
        "original_characters": original_characters,
        "analyzed_characters": len(text),
    }
