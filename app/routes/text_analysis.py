from __future__ import annotations

from pathlib import Path
from typing import Tuple

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi_limiter.depends import RateLimiter

from ..services import text_analysis as text_analysis_service
from ..services.model_registry import registry
from ..utils.errors import api_error
from ..utils.throttle import request_slot

router = APIRouter(tags=["text"])

ALLOWED_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".rst",
    ".log",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".tex",
    ".html",
    ".htm",
}

# Keep uploads light; we truncate bigger payloads in-memory and do not store them on disk
MAX_UPLOAD_BYTES = 512 * 1024  # 512 KB


async def _extract_text_payload(
    inline_text: str,
    uploaded_file: UploadFile | None,
) -> Tuple[str, bool, int]:
    """Merge inline text + uploaded content, ensuring we only keep text-sized payloads."""
    segments: list[str] = []
    truncated = False
    original_chars = 0

    if inline_text and inline_text.strip():
        cleaned = inline_text.strip()
        segments.append(cleaned)
        original_chars += len(cleaned)

    if uploaded_file:
        extension = Path(uploaded_file.filename or "").suffix.lower()
        if extension and extension not in ALLOWED_TEXT_EXTENSIONS:
            raise api_error(
                "Unsupported file type. Please upload a text-based file "
                "(txt, md, csv, json, html, yaml, log).",
                status_code=415,
                code="unsupported_file_type",
            )

        raw_bytes = await uploaded_file.read()
        if not raw_bytes:
            raise api_error("Uploaded file was empty", status_code=422, code="empty_upload")

        if len(raw_bytes) > MAX_UPLOAD_BYTES:
            raw_bytes = raw_bytes[:MAX_UPLOAD_BYTES]
            truncated = True

        try:
            decoded = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            decoded = raw_bytes.decode("latin-1", errors="ignore")

        cleaned = decoded.strip()
        if cleaned:
            segments.append(cleaned)
            original_chars += len(cleaned)

    if not segments:
        raise api_error(
            "Provide text or upload a text-based file to analyze",
            status_code=422,
            code="missing_text",
        )

    combined = "\n\n".join(segments)
    if len(combined) > text_analysis_service.MAX_ANALYSIS_CHARACTERS:
        combined = combined[: text_analysis_service.MAX_ANALYSIS_CHARACTERS]
        truncated = True

    return combined, truncated, original_chars


@router.post("/text/analyze", dependencies=[Depends(RateLimiter(times=5, seconds=10))])
async def analyze_text(
    model: str = Form(...),
    text: str = Form(""),
    text_file: UploadFile | None = File(None),
    ):
    entry = await registry.get_model(model)
    if not entry or "chat" not in entry.capabilities:
        raise api_error(
            "Requested model does not support chat",
            status_code=404,
            code="model_not_found",
        )

    combined_text, truncated, original_chars = await _extract_text_payload(text, text_file)

    async with request_slot():
        response = await text_analysis_service.analyze_text(
            entry,
            model,
            combined_text,
            truncated=truncated,
            original_characters=original_chars,
        )

    return response
