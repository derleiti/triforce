"""
Mail MCP Tool Handlers — wraps app.services.mail_service for MCP dispatch.
All blocking IMAP/SMTP calls are offloaded via asyncio.to_thread().

Tools:
  mail_inbox     - List recent emails from nova@ailinux.me
  mail_read      - Read full email by UID
  mail_send      - Send email from nova@ailinux.me
  mail_mark_seen - Mark email as read/seen
"""

import asyncio
import logging
from typing import Any, Dict

logger = logging.getLogger("ailinux.mcp.mail")


async def handle_mail_inbox(params: Dict[str, Any]) -> Dict:
    """List recent emails from nova@ailinux.me INBOX."""
    try:
        from app.services.mail_service import mail_inbox
        messages = await asyncio.to_thread(
            mail_inbox,
            limit=int(params.get("limit", 20)),
            folder=params.get("folder", "INBOX"),
        )
        return {"count": len(messages), "messages": messages}
    except Exception as e:
        logger.error(f"mail_inbox error: {e}")
        return {"error": str(e)}


async def handle_mail_read(params: Dict[str, Any]) -> Dict:
    """Read full email content by UID."""
    try:
        from app.services.mail_service import mail_read
        uid = params.get("uid", "")
        if not uid:
            return {"error": "Parameter 'uid' is required"}
        return await asyncio.to_thread(mail_read, str(uid), folder=params.get("folder", "INBOX"))
    except Exception as e:
        logger.error(f"mail_read error: {e}")
        return {"error": str(e)}


async def handle_mail_send(params: Dict[str, Any]) -> Dict:
    """Send email from nova@ailinux.me via SMTP."""
    try:
        from app.services.mail_service import mail_send
        to = params.get("to", "")
        subject = params.get("subject", "")
        body = params.get("body", "")
        if not to:
            return {"error": "Parameter 'to' is required"}
        if not subject:
            return {"error": "Parameter 'subject' is required"}
        return await asyncio.to_thread(
            mail_send,
            to=to, subject=subject, body=body,
            cc=params.get("cc"), reply_to=params.get("reply_to"),
        )
    except Exception as e:
        logger.error(f"mail_send error: {e}")
        return {"error": str(e)}


async def handle_mail_mark_seen(params: Dict[str, Any]) -> Dict:
    """Mark email as read/seen by UID."""
    try:
        from app.services.mail_service import mail_mark_seen
        uid = params.get("uid", "")
        if not uid:
            return {"error": "Parameter 'uid' is required"}
        return await asyncio.to_thread(mail_mark_seen, str(uid), folder=params.get("folder", "INBOX"))
    except Exception as e:
        logger.error(f"mail_mark_seen error: {e}")
        return {"error": str(e)}


MAIL_TOOL_HANDLERS = {
    "mail_inbox":     handle_mail_inbox,
    "mail_read":      handle_mail_read,
    "mail_send":      handle_mail_send,
    "mail_mark_seen": handle_mail_mark_seen,
}

MAIL_TOOL_NAMES = list(MAIL_TOOL_HANDLERS.keys())
