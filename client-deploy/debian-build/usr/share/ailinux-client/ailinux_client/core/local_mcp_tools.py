"""
Local MCP Tools for AILinux Client
==================================

Provides local filesystem operations via MCP protocol.
These tools run on the CLIENT side, not on the server.
"""
import os
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger("ailinux.local_mcp")

# Allowed base paths for security
ALLOWED_PATHS = [
    Path.home(),
    Path("/tmp"),
]

def _is_path_allowed(path: Path) -> bool:
    """Check if path is within allowed directories"""
    path = path.resolve()
    return any(path.is_relative_to(allowed) for allowed in ALLOWED_PATHS)

def _safe_path(path_str: str) -> Path:
    """Validate and return safe path"""
    path = Path(path_str).expanduser().resolve()
    if not _is_path_allowed(path):
        raise PermissionError(f"Access denied: {path}")
    return path


class LocalMCPTools:
    """
    Local MCP tool handlers for filesystem operations.
    """
    
    @staticmethod
    def list_tools() -> List[Dict[str, Any]]:
        """Return list of available local tools"""
        return [
            {
                "name": "local_file_read",
                "description": "Read a local file",
                "parameters": {"path": "string"}
            },
            {
                "name": "local_file_write",
                "description": "Write content to a local file",
                "parameters": {"path": "string", "content": "string", "append": "boolean"}
            },
            {
                "name": "local_file_delete",
                "description": "Delete a local file",
                "parameters": {"path": "string"}
            },
            {
                "name": "local_dir_list",
                "description": "List directory contents",
                "parameters": {"path": "string", "recursive": "boolean"}
            },
            {
                "name": "local_dir_create",
                "description": "Create a directory",
                "parameters": {"path": "string"}
            },
            {
                "name": "local_shell",
                "description": "Execute a shell command locally",
                "parameters": {"command": "string", "cwd": "string", "timeout": "integer"}
            },
            {
                "name": "local_file_copy",
                "description": "Copy a file or directory",
                "parameters": {"src": "string", "dst": "string"}
            },
            {
                "name": "local_file_move",
                "description": "Move/rename a file or directory",
                "parameters": {"src": "string", "dst": "string"}
            },
            {
                "name": "local_file_info",
                "description": "Get file/directory information",
                "parameters": {"path": "string"}
            },
            {
                "name": "local_search",
                "description": "Search for files by pattern",
                "parameters": {"path": "string", "pattern": "string", "recursive": "boolean"}
            },
        ]
    
    @staticmethod
    def file_read(path: str) -> Dict[str, Any]:
        """Read file contents"""
        try:
            safe_path = _safe_path(path)
            if not safe_path.exists():
                return {"error": f"File not found: {path}"}
            if not safe_path.is_file():
                return {"error": f"Not a file: {path}"}
            
            content = safe_path.read_text(errors="replace")
            return {
                "path": str(safe_path),
                "content": content,
                "size": safe_path.stat().st_size
            }
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def file_write(path: str, content: str, append: bool = False) -> Dict[str, Any]:
        """Write content to file"""
        try:
            safe_path = _safe_path(path)
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            
            mode = "a" if append else "w"
            with open(safe_path, mode) as f:
                f.write(content)
            
            return {
                "path": str(safe_path),
                "written": len(content),
                "append": append
            }
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def file_delete(path: str) -> Dict[str, Any]:
        """Delete file"""
        try:
            safe_path = _safe_path(path)
            if not safe_path.exists():
                return {"error": f"Not found: {path}"}
            
            if safe_path.is_file():
                safe_path.unlink()
            else:
                shutil.rmtree(safe_path)
            
            return {"deleted": str(safe_path)}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def dir_list(path: str, recursive: bool = False) -> Dict[str, Any]:
        """List directory contents"""
        try:
            safe_path = _safe_path(path)
            if not safe_path.exists():
                return {"error": f"Not found: {path}"}
            if not safe_path.is_dir():
                return {"error": f"Not a directory: {path}"}
            
            entries = []
            if recursive:
                for item in safe_path.rglob("*"):
                    entries.append({
                        "path": str(item.relative_to(safe_path)),
                        "type": "dir" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else 0
                    })
            else:
                for item in safe_path.iterdir():
                    entries.append({
                        "name": item.name,
                        "type": "dir" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else 0
                    })
            
            return {"path": str(safe_path), "entries": entries}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def dir_create(path: str) -> Dict[str, Any]:
        """Create directory"""
        try:
            safe_path = _safe_path(path)
            safe_path.mkdir(parents=True, exist_ok=True)
            return {"created": str(safe_path)}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def shell(command: str, cwd: str = None, timeout: int = 30) -> Dict[str, Any]:
        """Execute shell command"""
        try:
            work_dir = _safe_path(cwd) if cwd else Path.home()
            
            result = subprocess.run(
                command,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                "command": command,
                "cwd": str(work_dir),
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def file_copy(src: str, dst: str) -> Dict[str, Any]:
        """Copy file or directory"""
        try:
            src_path = _safe_path(src)
            dst_path = _safe_path(dst)
            
            if src_path.is_dir():
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)
            
            return {"copied": str(src_path), "to": str(dst_path)}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def file_move(src: str, dst: str) -> Dict[str, Any]:
        """Move/rename file or directory"""
        try:
            src_path = _safe_path(src)
            dst_path = _safe_path(dst)
            shutil.move(src_path, dst_path)
            return {"moved": str(src_path), "to": str(dst_path)}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def file_info(path: str) -> Dict[str, Any]:
        """Get file information"""
        try:
            safe_path = _safe_path(path)
            if not safe_path.exists():
                return {"error": f"Not found: {path}"}
            
            stat = safe_path.stat()
            return {
                "path": str(safe_path),
                "type": "dir" if safe_path.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "permissions": oct(stat.st_mode)[-3:]
            }
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def search(path: str, pattern: str, recursive: bool = True) -> Dict[str, Any]:
        """Search for files"""
        try:
            safe_path = _safe_path(path)
            if not safe_path.is_dir():
                return {"error": f"Not a directory: {path}"}
            
            matches = []
            glob_func = safe_path.rglob if recursive else safe_path.glob
            for match in glob_func(pattern):
                matches.append({
                    "path": str(match),
                    "type": "dir" if match.is_dir() else "file"
                })
            
            return {"pattern": pattern, "matches": matches[:100]}  # Limit results
        except Exception as e:
            return {"error": str(e)}


# Tool dispatcher
LOCAL_TOOL_HANDLERS = {
    "local_file_read": lambda p: LocalMCPTools.file_read(p.get("path", "")),
    "local_file_write": lambda p: LocalMCPTools.file_write(p.get("path", ""), p.get("content", ""), p.get("append", False)),
    "local_file_delete": lambda p: LocalMCPTools.file_delete(p.get("path", "")),
    "local_dir_list": lambda p: LocalMCPTools.dir_list(p.get("path", "~"), p.get("recursive", False)),
    "local_dir_create": lambda p: LocalMCPTools.dir_create(p.get("path", "")),
    "local_shell": lambda p: LocalMCPTools.shell(p.get("command", ""), p.get("cwd"), p.get("timeout", 30)),
    "local_file_copy": lambda p: LocalMCPTools.file_copy(p.get("src", ""), p.get("dst", "")),
    "local_file_move": lambda p: LocalMCPTools.file_move(p.get("src", ""), p.get("dst", "")),
    "local_file_info": lambda p: LocalMCPTools.file_info(p.get("path", "")),
    "local_search": lambda p: LocalMCPTools.search(p.get("path", "~"), p.get("pattern", "*"), p.get("recursive", True)),
}


def handle_local_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle local MCP tool call"""
    handler = LOCAL_TOOL_HANDLERS.get(tool_name)
    if not handler:
        return {"error": f"Unknown local tool: {tool_name}"}
    
    try:
        return handler(params)
    except Exception as e:
        logger.error(f"Local tool error: {tool_name} - {e}")
        return {"error": str(e)}
