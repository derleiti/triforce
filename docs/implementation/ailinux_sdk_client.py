# ailinux_sdk/client.py
"""
AILinux Client SDK - Einheitliches SDK für Desktop/Mobile Clients
Verbindet sich zum TriForce Server, kein API Key nötig

Stand: 2025-12-13
"""

import asyncio
import aiohttp
import json
import os
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ClientRole(str, Enum):
    DESKTOP = "desktop"
    MOBILE = "mobile"
    CLI_AGENT = "cli_agent"


@dataclass
class ClientConfig:
    """Client Konfiguration aus .env"""
    client_id: str
    client_secret: str
    server_url: str = "https://api.ailinux.me"
    device_name: str = "Desktop"
    device_type: str = "desktop"
    
    # Lokale Berechtigungen
    allow_bash: bool = True
    allow_file_read: bool = True
    allow_file_write: bool = False
    allow_logs: bool = True
    
    # Pfad-Beschränkungen
    allowed_paths: List[str] = None
    blocked_paths: List[str] = None
    
    @classmethod
    def from_env(cls, env_path: Path = None) -> "ClientConfig":
        """Lädt Config aus .env Datei"""
        from dotenv import load_dotenv
        
        if env_path:
            load_dotenv(env_path)
        else:
            # Standard-Pfade versuchen
            paths = [
                Path.home() / ".config/ailinux/.env",
                Path.home() / ".ailinux/.env",
                Path(".env")
            ]
            for p in paths:
                if p.exists():
                    load_dotenv(p)
                    break
        
        return cls(
            client_id=os.getenv("AILINUX_CLIENT_ID", ""),
            client_secret=os.getenv("AILINUX_CLIENT_SECRET", ""),
            server_url=os.getenv("AILINUX_SERVER", "https://api.ailinux.me"),
            device_name=os.getenv("AILINUX_DEVICE_NAME", platform.node()),
            device_type=os.getenv("AILINUX_DEVICE_TYPE", "desktop"),
            allow_bash=os.getenv("ALLOW_BASH", "true").lower() == "true",
            allow_file_read=os.getenv("ALLOW_FILE_READ", "true").lower() == "true",
            allow_file_write=os.getenv("ALLOW_FILE_WRITE", "false").lower() == "true",
            allow_logs=os.getenv("ALLOW_LOGS", "true").lower() == "true",
            allowed_paths=os.getenv("ALLOWED_PATHS", "/home,/tmp").split(","),
            blocked_paths=os.getenv("BLOCKED_PATHS", "/etc/shadow,/root").split(","),
        )
    
    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id,
            "server_url": self.server_url,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "allow_bash": self.allow_bash,
            "allow_file_read": self.allow_file_read,
            "allow_file_write": self.allow_file_write,
            "allow_logs": self.allow_logs
        }


class AILinuxClient:
    """
    AILinux Client - Verbindet sich zum TriForce Server
    
    Der Client hat KEINE API Keys - diese sind sicher auf dem Server.
    Client authentifiziert sich nur mit client_id/secret.
    
    Usage:
        client = AILinuxClient()
        await client.connect()
        
        # Chat mit KI
        response = await client.chat("Hallo Nova!")
        
        # Task anfordern
        task = await client.request_task("Optimiere meinen PC für Gaming")
    """
    
    def __init__(self, config: ClientConfig = None):
        self.config = config or ClientConfig.from_env()
        self.session: Optional[aiohttp.ClientSession] = None
        self.token: Optional[str] = None
        self.connected = False
        self.client_info: Optional[dict] = None
        
        # Callbacks
        self.on_message: Optional[Callable[[dict], None]] = None
        self.on_task_update: Optional[Callable[[dict], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
    
    # =========================================================================
    # Connection Management
    # =========================================================================
    
    async def connect(self) -> bool:
        """
        Zum Server verbinden und authentifizieren
        
        Returns:
            True wenn erfolgreich verbunden
        """
        if not self.config.client_id or not self.config.client_secret:
            logger.error("client_id and client_secret required")
            return False
        
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        try:
            response = await self.session.post(
                f"{self.config.server_url}/v1/auth/client",
                json={
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "device_name": self.config.device_name,
                    "capabilities": self._get_capabilities()
                }
            )
            
            if response.status == 200:
                data = await response.json()
                self.token = data["access_token"]
                self.client_info = {
                    "role": data["role"],
                    "allowed_tools": data["allowed_tools"]
                }
                self.connected = True
                logger.info(f"Connected as {self.config.client_id} (role: {data['role']})")
                return True
            else:
                error = await response.text()
                logger.error(f"Auth failed: {error}")
                if self.on_error:
                    self.on_error(f"Auth failed: {error}")
                return False
                
        except aiohttp.ClientError as e:
            logger.error(f"Connection failed: {e}")
            if self.on_error:
                self.on_error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Verbindung trennen"""
        if self.session:
            await self.session.close()
        self.session = None
        self.token = None
        self.connected = False
        logger.info("Disconnected")
    
    async def reconnect(self) -> bool:
        """Verbindung neu aufbauen"""
        await self.disconnect()
        return await self.connect()
    
    def _get_capabilities(self) -> List[str]:
        """Liste der Client-Fähigkeiten"""
        caps = ["chat", "system_info"]
        
        if self.config.allow_bash:
            caps.append("bash")
        if self.config.allow_file_read:
            caps.append("file_read")
        if self.config.allow_file_write:
            caps.append("file_write")
        if self.config.allow_logs:
            caps.append("logs")
        
        return caps
    
    # =========================================================================
    # API Calls
    # =========================================================================
    
    async def _call(self, method: str, params: dict = None) -> dict:
        """
        MCP-Call zum Server
        
        Args:
            method: MCP Methode (z.B. "tools/call")
            params: Parameter
        
        Returns:
            Result-Dict
        
        Raises:
            RuntimeError bei Fehlern
        """
        if not self.connected:
            raise RuntimeError("Not connected - call connect() first")
        
        try:
            response = await self.session.post(
                f"{self.config.server_url}/v1/mcp",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params or {},
                    "id": 1
                }
            )
            
            data = await response.json()
            
            if "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                if self.on_error:
                    self.on_error(error_msg)
                raise RuntimeError(error_msg)
            
            return data.get("result", {})
            
        except aiohttp.ClientError as e:
            if self.on_error:
                self.on_error(str(e))
            raise RuntimeError(f"API call failed: {e}")
    
    async def call_tool(self, tool_name: str, arguments: dict = None) -> dict:
        """
        Ein Tool aufrufen
        
        Args:
            tool_name: Name des Tools
            arguments: Tool-Argumente
        
        Returns:
            Tool-Result
        """
        return await self._call("tools/call", {
            "name": tool_name,
            "arguments": arguments or {}
        })
    
    # =========================================================================
    # Chat API
    # =========================================================================
    
    async def chat(
        self,
        message: str,
        model: str = None,
        system_prompt: str = None,
        prefer_local: bool = False,
        prefer_cloud: bool = False
    ) -> str:
        """
        Chat mit KI
        
        Server wählt automatisch das beste Model oder nutzt das angegebene.
        API Keys sind sicher auf dem Server - Client braucht keine.
        
        Args:
            message: Die Nachricht
            model: Optional: Explizites Model (z.B. "ollama/qwen2.5:14b")
            system_prompt: Optional: System-Prompt
            prefer_local: Lokale Modelle bevorzugen
            prefer_cloud: Cloud-APIs bevorzugen
        
        Returns:
            KI-Antwort als String
        """
        result = await self.call_tool("chat_smart", {
            "message": message,
            "model": model,
            "system_prompt": system_prompt,
            "prefer_local": prefer_local,
            "prefer_cloud": prefer_cloud
        })
        
        return result.get("response", "")
    
    async def chat_with_model(self, message: str, model: str) -> str:
        """Chat mit spezifischem Model"""
        return await self.chat(message, model=model)
    
    async def chat_local(self, message: str) -> str:
        """Chat nur mit lokalen Modellen (Ollama)"""
        return await self.chat(message, prefer_local=True)
    
    async def chat_cloud(self, message: str, model: str = None) -> str:
        """Chat mit Cloud-APIs"""
        return await self.chat(message, model=model, prefer_cloud=True)
    
    # =========================================================================
    # Task API
    # =========================================================================
    
    async def request_task(
        self,
        description: str,
        agent: str = "claude",
        include_logs: bool = False,
        include_system_info: bool = True
    ) -> dict:
        """
        Task an Server senden
        
        Server spawnt einen Agent (Claude, Codex, etc.) mit seinen API Keys.
        Agent arbeitet autonom bis Task erledigt.
        
        Args:
            description: Was soll gemacht werden?
            agent: Agent-Typ (claude, codex, gemini, opencode)
            include_logs: Lokale Logs mitsenden?
            include_system_info: System-Info mitsenden?
        
        Returns:
            Task-Info mit task_id
        """
        context = {}
        
        if include_system_info:
            context["client_system"] = await self._get_local_system_info()
        
        if include_logs:
            context["logs"] = await self._get_local_logs()
        
        return await self.call_tool("client_request_task", {
            "client_id": self.config.client_id,
            "description": description,
            "agent_type": agent,
            "context": context
        })
    
    async def get_task_status(self, task_id: str) -> dict:
        """Task-Status abfragen"""
        return await self.call_tool("client_task_status", {"task_id": task_id})
    
    async def get_task_output(self, task_id: str, last_n: int = 50) -> List[str]:
        """Task-Output holen"""
        result = await self.call_tool("client_task_output", {
            "task_id": task_id,
            "last_n": last_n
        })
        return result.get("output", [])
    
    async def list_tasks(self, status: str = None) -> List[dict]:
        """Eigene Tasks auflisten"""
        result = await self.call_tool("client_list_tasks", {
            "client_id": self.config.client_id,
            "status": status
        })
        return result.get("tasks", [])
    
    async def cancel_task(self, task_id: str) -> bool:
        """Task abbrechen"""
        result = await self.call_tool("client_cancel_task", {"task_id": task_id})
        return result.get("success", False)
    
    async def wait_for_task(self, task_id: str, poll_interval: float = 2.0) -> dict:
        """
        Warten bis Task fertig ist
        
        Args:
            task_id: Task-ID
            poll_interval: Abfrage-Intervall in Sekunden
        
        Returns:
            Finaler Task-Status
        """
        while True:
            status = await self.get_task_status(task_id)
            
            if self.on_task_update:
                self.on_task_update(status)
            
            if status.get("status") in ("completed", "failed", "cancelled"):
                return status
            
            await asyncio.sleep(poll_interval)
    
    # =========================================================================
    # Utility Tools
    # =========================================================================
    
    async def weather(self, location: str = None) -> dict:
        """Wetter abfragen"""
        args = {}
        if location:
            args["location"] = location
        return await self.call_tool("weather", args)
    
    async def current_time(self, timezone: str = "Europe/Berlin") -> dict:
        """Aktuelle Zeit"""
        return await self.call_tool("current_time", {"timezone": timezone})
    
    async def web_search(self, query: str, max_results: int = 10) -> dict:
        """Web-Suche"""
        return await self.call_tool("smart_search", {
            "query": query,
            "max_results": max_results
        })
    
    async def list_models(self, include_cloud: bool = True) -> List[dict]:
        """Verfügbare Chat-Modelle auflisten"""
        result = await self.call_tool("chat_list_models", {
            "include_cloud": include_cloud
        })
        return result.get("models", [])
    
    # =========================================================================
    # Lokale Helfer
    # =========================================================================
    
    async def _get_local_system_info(self) -> dict:
        """System-Info für Task-Kontext sammeln"""
        import platform
        
        info = {
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "arch": platform.machine(),
            "python": platform.python_version()
        }
        
        # Mit psutil erweitern falls verfügbar
        try:
            import psutil
            info.update({
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
                "ram_percent": psutil.virtual_memory().percent,
                "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 1)
            })
        except ImportError:
            pass
        
        return info
    
    async def _get_local_logs(self, since: str = "30m", priority: str = "warning") -> str:
        """Lokale Logs für Task-Kontext"""
        if not self.config.allow_logs:
            return ""
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "journalctl", "--no-pager", f"--since=-{since}",
                "-p", priority, "-o", "short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            lines = stdout.decode().strip().split('\n')
            return "\n".join(lines[-50:])  # Letzte 50 Zeilen
        except Exception as e:
            logger.warning(f"Could not collect logs: {e}")
            return ""
    
    # =========================================================================
    # Context Manager
    # =========================================================================
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()


# =============================================================================
# Convenience Functions
# =============================================================================

async def quick_chat(message: str, model: str = None) -> str:
    """
    Schneller Chat ohne explizites Client-Management
    
    Usage:
        response = await quick_chat("Hallo Nova!")
    """
    async with AILinuxClient() as client:
        return await client.chat(message, model=model)


async def quick_task(description: str, agent: str = "claude") -> dict:
    """
    Schneller Task ohne explizites Client-Management
    
    Usage:
        result = await quick_task("Analysiere meine Logs")
    """
    async with AILinuxClient() as client:
        task = await client.request_task(description, agent=agent)
        return await client.wait_for_task(task["task_id"])


# =============================================================================
# CLI für Tests
# =============================================================================

if __name__ == "__main__":
    import sys
    
    async def main():
        client = AILinuxClient()
        
        if not await client.connect():
            print("❌ Verbindung fehlgeschlagen")
            sys.exit(1)
        
        print(f"✅ Verbunden als {client.config.client_id}")
        
        # Test-Chat
        if len(sys.argv) > 1:
            message = " ".join(sys.argv[1:])
            print(f"\n📤 Sende: {message}")
            response = await client.chat(message)
            print(f"📥 Antwort: {response}")
        else:
            print("\nUsage: python client.py <nachricht>")
        
        await client.disconnect()
    
    asyncio.run(main())


# ============================================================================
# LOCAL TOOLS - Laufen auf dem Client, nicht auf dem Server
# ============================================================================

LOCAL_TOOLS = {
    "codebase_structure",
    "codebase_file", 
    "codebase_search",
    "codebase_edit",
    "codebase_create",
    "codebase_backup",
    "code_scout",
    "code_probe",
    "ram_search",
    "bash_exec",
    "file_read",
    "file_write",
}


class LocalToolHandler:
    """Führt Tools lokal auf dem Client aus statt auf dem Server."""
    
    def __init__(self, config: ClientConfig, base_path: Path = None):
        self.config = config
        self.base_path = base_path or Path.home()
        self.allowed_extensions = {
            ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".md", ".txt",
            ".html", ".css", ".sh", ".bash", ".toml", ".cfg", ".ini",
            ".c", ".cpp", ".h", ".rs", ".go", ".java", ".kt", ".swift"
        }
    
    def is_local_tool(self, tool_name: str) -> bool:
        """Prüft ob Tool lokal ausgeführt werden soll."""
        return tool_name in LOCAL_TOOLS
    
    async def execute(self, tool_name: str, arguments: dict) -> dict:
        """Führt lokales Tool aus."""
        handlers = {
            "codebase_structure": self._handle_structure,
            "codebase_file": self._handle_file,
            "codebase_search": self._handle_search,
            "codebase_edit": self._handle_edit,
            "codebase_create": self._handle_create,
            "code_scout": self._handle_structure,  # Alias
            "bash_exec": self._handle_bash,
            "file_read": self._handle_file,
            "file_write": self._handle_write,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            raise ValueError(f"Local tool not implemented: {tool_name}")
        
        return await handler(arguments)
    
    def _safe_path(self, path_str: str) -> Path:
        """Validiert Pfad gegen Konfiguration."""
        path = Path(path_str).resolve()
        
        # Blocked paths prüfen
        for blocked in (self.config.blocked_paths or []):
            if blocked and str(path).startswith(blocked.strip()):
                raise PermissionError(f"Path blocked: {path}")
        
        # Allowed paths prüfen
        allowed = False
        for allowed_path in (self.config.allowed_paths or []):
            if allowed_path and str(path).startswith(allowed_path.strip()):
                allowed = True
                break
        
        if not allowed and self.config.allowed_paths:
            raise PermissionError(f"Path not in allowed list: {path}")
        
        return path
    
    async def _handle_structure(self, params: dict) -> dict:
        """Lokale Directory-Struktur."""
        path = params.get("path", ".")
        max_depth = params.get("max_depth", 3)
        include_files = params.get("include_files", True)
        
        safe_path = self._safe_path(path)
        if not safe_path.exists():
            raise ValueError(f"Path not found: {path}")
        
        lines = [f"{safe_path.name}/"]
        
        def build_tree(dir_path: Path, prefix: str = "", depth: int = 0):
            if depth > max_depth:
                return
            
            try:
                items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                items = [i for i in items if not i.name.startswith(".") and i.name != "__pycache__"]
                
                for i, item in enumerate(items):
                    is_last = (i == len(items) - 1)
                    connector = "└── " if is_last else "├── "
                    
                    if item.is_dir():
                        lines.append(f"{prefix}{connector}{item.name}/")
                        new_prefix = prefix + ("    " if is_last else "│   ")
                        build_tree(item, new_prefix, depth + 1)
                    elif include_files and item.suffix in self.allowed_extensions:
                        lines.append(f"{prefix}{connector}{item.name}")
            except PermissionError:
                lines.append(f"{prefix}└── (access denied)")
        
        build_tree(safe_path)
        
        return {
            "root": str(safe_path),
            "structure": "\n".join(lines),
            "local": True
        }
    
    async def _handle_file(self, params: dict) -> dict:
        """Lokale Datei lesen."""
        if not self.config.allow_file_read:
            raise PermissionError("File read not allowed")
        
        path = params.get("path")
        if not path:
            raise ValueError("'path' required")
        
        safe_path = self._safe_path(path)
        if not safe_path.exists():
            raise ValueError(f"File not found: {path}")
        
        if safe_path.suffix not in self.allowed_extensions:
            raise ValueError(f"File type not allowed: {safe_path.suffix}")
        
        content = safe_path.read_text(encoding="utf-8")
        
        return {
            "path": str(safe_path),
            "content": content,
            "size": len(content),
            "lines": content.count("\n") + 1,
            "local": True
        }
    
    async def _handle_search(self, params: dict) -> dict:
        """Lokale Code-Suche."""
        import re
        
        query = params.get("query")
        path = params.get("path", ".")
        max_results = params.get("max_results", 50)
        
        if not query:
            raise ValueError("'query' required")
        
        safe_path = self._safe_path(path)
        pattern = re.compile(query, re.IGNORECASE)
        results = []
        
        for file_path in safe_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in self.allowed_extensions:
                try:
                    lines = file_path.read_text(encoding="utf-8").splitlines()
                    for i, line in enumerate(lines):
                        if pattern.search(line):
                            results.append({
                                "file": str(file_path.relative_to(safe_path)),
                                "line": i + 1,
                                "match": line.strip()[:200]
                            })
                            if len(results) >= max_results:
                                break
                except (PermissionError, UnicodeDecodeError):
                    continue
            
            if len(results) >= max_results:
                break
        
        return {
            "query": query,
            "results": results,
            "count": len(results),
            "local": True
        }
    
    async def _handle_edit(self, params: dict) -> dict:
        """Lokale Datei bearbeiten."""
        if not self.config.allow_file_write:
            raise PermissionError("File write not allowed")
        
        path = params.get("path")
        mode = params.get("mode")
        
        if not path or not mode:
            raise ValueError("'path' and 'mode' required")
        
        safe_path = self._safe_path(path)
        
        if not safe_path.exists():
            raise ValueError(f"File not found: {path}")
        
        original = safe_path.read_text(encoding="utf-8")
        
        if mode == "replace":
            old_text = params.get("old_text", "")
            new_text = params.get("new_text", "")
            if old_text not in original:
                raise ValueError("old_text not found in file")
            new_content = original.replace(old_text, new_text, 1)
        
        elif mode == "append":
            new_text = params.get("new_text", "")
            new_content = original + "\n" + new_text
        
        else:
            raise ValueError(f"Unknown mode: {mode}")
        
        # Backup erstellen
        backup_path = safe_path.with_suffix(safe_path.suffix + ".bak")
        backup_path.write_text(original, encoding="utf-8")
        
        # Schreiben
        safe_path.write_text(new_content, encoding="utf-8")
        
        return {
            "path": str(safe_path),
            "mode": mode,
            "backup": str(backup_path),
            "local": True
        }
    
    async def _handle_create(self, params: dict) -> dict:
        """Lokale Datei erstellen."""
        if not self.config.allow_file_write:
            raise PermissionError("File write not allowed")
        
        path = params.get("path")
        content = params.get("content", "")
        
        if not path:
            raise ValueError("'path' required")
        
        safe_path = self._safe_path(path)
        
        if safe_path.exists():
            raise ValueError(f"File already exists: {path}")
        
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text(content, encoding="utf-8")
        
        return {
            "path": str(safe_path),
            "created": True,
            "local": True
        }
    
    async def _handle_write(self, params: dict) -> dict:
        """Alias für file write."""
        return await self._handle_create(params)
    
    async def _handle_bash(self, params: dict) -> dict:
        """Lokales Bash-Kommando ausführen."""
        if not self.config.allow_bash:
            raise PermissionError("Bash execution not allowed")
        
        import subprocess
        
        command = params.get("command")
        timeout = params.get("timeout", 30)
        
        if not command:
            raise ValueError("'command' required")
        
        # Gefährliche Kommandos blocken
        dangerous = ["rm -rf /", "mkfs", "> /dev/", "dd if="]
        for d in dangerous:
            if d in command:
                raise PermissionError(f"Dangerous command blocked: {d}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.base_path)
            )
            
            return {
                "command": command,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "local": True
            }
        except subprocess.TimeoutExpired:
            return {
                "command": command,
                "error": f"Timeout after {timeout}s",
                "local": True
            }


# ============================================================================
# ERWEITERTE AILinuxClient Methode für Tool-Routing
# ============================================================================

async def call_tool_smart(client: AILinuxClient, tool_name: str, arguments: dict = None) -> dict:
    """
    Intelligentes Tool-Routing:
    - Lokale Tools → LocalToolHandler (Client)
    - Server Tools → TriForce Server
    
    Usage:
        result = await call_tool_smart(client, "codebase_structure", {"path": "."})
        # → Läuft LOKAL auf dem Client
        
        result = await call_tool_smart(client, "chat", {"message": "Hallo"})
        # → Läuft auf dem SERVER
    """
    arguments = arguments or {}
    
    # Lokaler Handler
    local_handler = LocalToolHandler(client.config, client.config.allowed_paths[0] if client.config.allowed_paths else None)
    
    if local_handler.is_local_tool(tool_name):
        # Lokal ausführen
        logger.info(f"[LOCAL] Executing {tool_name}")
        return await local_handler.execute(tool_name, arguments)
    else:
        # Server-Aufruf
        logger.info(f"[SERVER] Calling {tool_name}")
        return await client.call_tool(tool_name, arguments)


# Convenience-Funktionen für häufige Operationen
async def local_code_search(client: AILinuxClient, query: str, path: str = ".") -> dict:
    """Schnelle lokale Code-Suche."""
    return await call_tool_smart(client, "codebase_search", {"query": query, "path": path})


async def local_file_edit(client: AILinuxClient, path: str, old_text: str, new_text: str) -> dict:
    """Schnelle lokale Datei-Bearbeitung."""
    return await call_tool_smart(client, "codebase_edit", {
        "path": path, 
        "mode": "replace",
        "old_text": old_text,
        "new_text": new_text
    })


async def local_bash(client: AILinuxClient, command: str, timeout: int = 30) -> dict:
    """Schnelles lokales Bash-Kommando."""
    return await call_tool_smart(client, "bash_exec", {"command": command, "timeout": timeout})


async def server_chat(client: AILinuxClient, message: str, model: str = None) -> str:
    """Chat über Server (nutzt Server-API-Keys)."""
    params = {"message": message}
    if model:
        params["model"] = model
    result = await call_tool_smart(client, "chat_smart", params)
    return result.get("response", "")


# Export der neuen Funktionen
__all__ = [
    "AILinuxClient", 
    "ClientConfig", 
    "LocalToolHandler",
    "LOCAL_TOOLS",
    "call_tool_smart",
    "local_code_search",
    "local_file_edit", 
    "local_bash",
    "server_chat",
    "quick_chat",
    "quick_task"
]
