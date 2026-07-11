"""
MCP Agent Session Identity Mapping (Phase 3, 2026-05)
======================================================

Maps incoming MCP sessions to Group Chat agent identities based on
clientInfo and User-Agent headers received during initialize handshake.

Mapping:
  openai-mcp / openai / chatgpt    -> chatgpt-web
  Mistral / le-chat                -> mistral-web
  claude.ai / anthropic            -> claude-web
  cursor                           -> cursor (no auto-join)
  unknown                          -> None
"""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("ailinux.mcp.agent_session")

DEFAULT_USER_SESSION = "gc-user-zombie"
_session_bindings: Dict[str, str] = {}


def map_client_to_agent(client_info: Optional[Dict[str, Any]],
                         user_agent: Optional[str]) -> Optional[str]:
    name = ((client_info or {}).get("name") or "").lower()
    ua = (user_agent or "").lower()
    if "openai-mcp" in name or "openai" in ua or "chatgpt" in ua:
        return "chatgpt-web"
    if "mistral" in name or "le-chat" in ua or "lechat" in ua:
        return "mistral-web"
    if "claude.ai" in ua or "anthropic" in ua or "claude-web" in name:
        return "claude-web"
    if "cursor" in name or "cursor" in ua:
        return "cursor"
    return None


def attach(mcp_session_id: Optional[str],
           client_info: Optional[Dict[str, Any]],
           user_agent: Optional[str]) -> Optional[str]:
    """Bind MCP session to agent identity. Returns agent_id or None."""
    agent_id = map_client_to_agent(client_info, user_agent)
    if not agent_id:
        return None
    if mcp_session_id:
        _session_bindings[mcp_session_id] = agent_id
        logger.info(f"AGENT_BIND | Session: {mcp_session_id} -> {agent_id}")
    try:
        _ensure_in_default_session(agent_id)
    except Exception as e:
        logger.warning(f"Auto-join failed for {agent_id}: {e}")
    return agent_id


def get_agent(mcp_session_id: Optional[str]) -> Optional[str]:
    if not mcp_session_id:
        return None
    return _session_bindings.get(mcp_session_id)


def _ensure_in_default_session(agent_id: str) -> None:
    """Add agent to gc-user-zombie session, creating it if needed."""
    from app.services.group_chat import group_chat, DEFAULT_PARTICIPANTS

    session = group_chat.get_session(DEFAULT_USER_SESSION)
    if not session:
        session = group_chat.create_session(
            topic="User Zombie - Persistent Multi-AI Chat",
            participants=["gemini-lead"],
        )
        old_id = session.id
        session.id = DEFAULT_USER_SESSION
        group_chat.sessions[DEFAULT_USER_SESSION] = session
        group_chat.sessions.pop(old_id, None)
        group_chat._save_session(session)
        logger.info(f"Created persistent default session: {DEFAULT_USER_SESSION}")

    if agent_id not in session.participants and agent_id in DEFAULT_PARTICIPANTS:
        session.participants[agent_id] = DEFAULT_PARTICIPANTS[agent_id]
        group_chat._save_session(session)
        logger.info(f"Auto-joined {agent_id} into {DEFAULT_USER_SESSION}")


def stats() -> Dict[str, Any]:
    return {
        "active_bindings": len(_session_bindings),
        "default_session": DEFAULT_USER_SESSION,
        "bindings": dict(_session_bindings),
    }
