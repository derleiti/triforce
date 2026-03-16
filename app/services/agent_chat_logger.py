"""
Agent Chat Logger
=================
Schreibt AI-Outputs (kein User-Input) verschlüsselt in .chatlog Dateien.

- Speicherort: /run/triforce/chatlogs/ (tmpfs, auto-cleared on reboot)
- Verschlüsselung: AES-256-GCM mit Key aus CHAT_LOG_KEY (triforce.env)
- Cleanup: nach 2h automatisch
- Format: Markdown-style, MCP-streambar

Hooks in:
- group_chat_auto_response.py  → API/Ollama-Agent Outputs
- group_chat.py                → Group Chat Messages
- agents.log via cli-agent interceptor
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ailinux.agent_chat_logger")

CHATLOG_DIR = Path("/run/triforce/chatlogs")
CLEANUP_AFTER_SECONDS = 7200  # 2h


def _get_aes_key() -> bytes:
    """AES-256 Key aus CHAT_LOG_KEY env (32 Bytes, base64 oder raw)."""
    key_str = os.getenv("CHAT_LOG_KEY", "")
    if not key_str:
        # Fallback: Key aus FEDERATION_SECRET ableiten
        secret = os.getenv("FEDERATION_SECRET", "triforce-default-key-32bytes!!")
        key_str = secret
    # Exakt 32 Bytes erzwingen
    raw = key_str.encode()[:32].ljust(32, b"\x00")
    return raw


def _encrypt(plaintext: str, key: bytes) -> str:
    """AES-256-GCM Verschlüsselung → base64-encoded JSON."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import secrets as _sec
        nonce = _sec.token_bytes(12)
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
        payload = base64.b64encode(nonce + ct).decode()
        return payload
    except ImportError:
        # Fallback ohne cryptography: base64 (kein echtes AES)
        return base64.b64encode(plaintext.encode()).decode()


def _decrypt(payload: str, key: bytes) -> str:
    """AES-256-GCM Entschlüsselung."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        raw = base64.b64decode(payload)
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ct, None).decode()
    except ImportError:
        return base64.b64decode(payload).decode()
    except Exception:
        return "[DECRYPT ERROR]"


class AgentChatLogger:
    """Zentraler Logger für alle AI-Agent Outputs."""

    def __init__(self):
        self._key = _get_aes_key()
        self._ensure_dir()

    def _ensure_dir(self):
        CHATLOG_DIR.mkdir(parents=True, exist_ok=True)
        CHATLOG_DIR.chmod(0o700)

    def _session_path(self, session_id: str) -> Path:
        # Sicherer Dateiname
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
        return CHATLOG_DIR / f"{safe}.chatlog"

    def _write_line(self, session_id: str, line: str):
        """Eine verschlüsselte Zeile an die Log-Datei anhängen."""
        path = self._session_path(session_id)
        encrypted = _encrypt(line, self._key)
        with open(path, "a") as f:
            f.write(encrypted + "\n")
        path.chmod(0o600)

    def log_message(
        self,
        session_id: str,
        agent_id: str,
        content: str,
        model: Optional[str] = None,
        msg_type: str = "response",
    ):
        """AI-Output loggen (kein User-Input)."""
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        model_tag = f" `{model}`" if model else ""
        # Markdown-Format
        header = f"\n### [{ts}] **{agent_id}**{model_tag}"
        body = content.strip()
        # Typ-spezifisches Styling
        if msg_type == "analysis":
            body = f"> {body.replace(chr(10), chr(10) + '> ')}"
        elif msg_type == "error":
            body = f"⚠️ {body}"
        line_data = json.dumps({
            "ts": ts,
            "agent": agent_id,
            "model": model,
            "type": msg_type,
            "header": header,
            "body": body,
        })
        self._write_line(session_id, line_data)
        logger.debug(f"ChatLog [{session_id}] {agent_id}: {len(content)} chars")

    def log_session_start(self, session_id: str, topic: str, participants: list):
        """Session-Header schreiben."""
        ts = datetime.now(timezone.utc).isoformat()
        header = f"# Group Chat: {topic}\n**Session:** `{session_id}`  \n**Start:** {ts}  \n**Participants:** {', '.join(participants)}\n\n---"
        line_data = json.dumps({
            "ts": ts,
            "type": "session_start",
            "header": header,
            "body": "",
            "agent": "system",
            "model": None,
        })
        self._write_line(session_id, line_data)

    def log_summary(self, session_id: str, summary: str):
        """Task-Zusammenfassung am Ende loggen."""
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        line_data = json.dumps({
            "ts": ts,
            "type": "summary",
            "header": f"\n## [{ts}] 📋 Task Summary",
            "body": summary,
            "agent": "system",
            "model": None,
        })
        self._write_line(session_id, line_data)

    def read_session(self, session_id: str, last_n: int = 0) -> list[dict]:
        """Entschlüsselte Log-Einträge lesen."""
        path = self._session_path(session_id)
        if not path.exists():
            return []
        entries = []
        lines = path.read_text().splitlines()
        if last_n:
            lines = lines[-last_n:]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                decrypted = _decrypt(line, self._key)
                entries.append(json.loads(decrypted))
            except Exception:
                continue
        return entries

    def render_markdown(self, session_id: str, last_n: int = 0) -> str:
        """Vollständige Markdown-Darstellung einer Session."""
        entries = self.read_session(session_id, last_n)
        parts = []
        for e in entries:
            header = e.get("header", "")
            body = e.get("body", "")
            if header:
                parts.append(header)
            if body:
                parts.append(body)
        return "\n".join(parts) if parts else "*Keine Logs für diese Session.*"

    def list_sessions(self) -> list[dict]:
        """Alle aktiven Log-Sessions auflisten."""
        self._ensure_dir()
        sessions = []
        now = time.time()
        for f in sorted(CHATLOG_DIR.glob("*.chatlog"), key=lambda x: x.stat().st_mtime, reverse=True):
            age = now - f.stat().st_mtime
            sessions.append({
                "session_id": f.stem,
                "size_bytes": f.stat().st_size,
                "age_minutes": round(age / 60, 1),
                "path": str(f),
            })
        return sessions

    def cleanup_old(self):
        """Logs älter als 2h löschen."""
        self._ensure_dir()
        now = time.time()
        removed = 0
        for f in CHATLOG_DIR.glob("*.chatlog"):
            if now - f.stat().st_mtime > CLEANUP_AFTER_SECONDS:
                f.unlink()
                removed += 1
        if removed:
            logger.info(f"ChatLog cleanup: {removed} alte Sessions gelöscht")
        return removed

    async def cleanup_loop(self):
        """Background-Task: Cleanup alle 30 Minuten."""
        while True:
            await asyncio.sleep(1800)
            try:
                self.cleanup_old()
            except Exception as e:
                logger.warning(f"ChatLog cleanup error: {e}")


# Singleton
_logger_instance: Optional[AgentChatLogger] = None


def get_chat_logger() -> AgentChatLogger:
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = AgentChatLogger()
    return _logger_instance
