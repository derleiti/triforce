from __future__ import annotations

import logging
import re
from typing import Optional

from fastapi import HTTPException, status

logger = logging.getLogger("ailinux.errors")

# Patterns that might leak sensitive information
SENSITIVE_PATTERNS = [
    r"api[_-]?key[=:\s]+\S+",
    r"password[=:\s]+\S+",
    r"token[=:\s]+\S+",
    r"secret[=:\s]+\S+",
    r"bearer\s+\S+",
    r"\b(?:\d{1,3}\.){3}\d{1,3}\b",  # IP addresses
    r"/home/\S+",  # File paths
    r"/var/\S+",
    r"/etc/\S+",
    r"traceback",
    r"stack trace",
]


def _sanitize_error_message(message: str) -> str:
    """Remove potentially sensitive information from error messages.

    This prevents leaking internal details like file paths, IP addresses,
    API keys, or stack traces to end users.
    """
    sanitized = message

    for pattern in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

    # Truncate very long messages that might contain stack traces
    if len(sanitized) > 500:
        sanitized = sanitized[:500] + "... [truncated]"

    return sanitized


def api_error(
    message: str,
    *,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    code: str = "bad_request",
    internal_message: Optional[str] = None,
    sanitize: bool = True,
) -> HTTPException:
    """Create an API error with optional message sanitization.

    Args:
        message: The error message to show to users
        status_code: HTTP status code
        code: Error code for programmatic handling
        internal_message: Optional detailed message for logging only
        sanitize: Whether to sanitize the message (default True)

    Returns:
        HTTPException with sanitized error details
    """
    # Log the full internal message if provided
    if internal_message:
        logger.error(f"[{code}] Internal: {internal_message}")

    # Sanitize the user-facing message
    user_message = _sanitize_error_message(message) if sanitize else message

    return HTTPException(
        status_code=status_code,
        detail={"error": {"message": user_message, "code": code}}
    )


def safe_api_error(
    user_message: str,
    internal_details: str,
    *,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    code: str = "internal_error",
) -> HTTPException:
    """Create an API error with separate user and internal messages.

    Use this for errors where you want to show a generic message to users
    but log detailed information internally.

    Args:
        user_message: Safe message to show to users
        internal_details: Detailed information for logs only
        status_code: HTTP status code
        code: Error code for programmatic handling

    Returns:
        HTTPException with safe user message
    """
    logger.error(f"[{code}] {internal_details}")
    return HTTPException(
        status_code=status_code,
        detail={"error": {"message": user_message, "code": code}}
    )
