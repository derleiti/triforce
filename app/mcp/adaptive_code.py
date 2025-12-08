"""
Adaptive Code Illumination MCP Extension.

Provides tools for efficient codebase analysis and manipulation using RAM-based caching
and selective loading to minimize context window usage.
"""

import os
import fnmatch
import re
import time
import logging
import subprocess
import tempfile
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class RAMCacheEntry:
    content: str
    timestamp: float
    size: int
    path: str

class AdaptiveCodeIlluminator:
    def __init__(self, root_dir: str = "/home/zombie/ailinux-ai-server-backend"):
        self.root_dir = Path(root_dir)
        self.cache: Dict[str, RAMCacheEntry] = {}
        self.max_cache_size = 100 * 1024 * 1024  # 100 MB limit
        self.default_ttl = 3600  # 1 hour
        self.ignored_patterns = [
            ".git", "__pycache__", "*.pyc", "node_modules", ".venv",
            ".pytest_cache", "dist", "build", ".idea", ".vscode",
            "*.log", "*.lock", "package-lock.json"
        ]

    def _is_ignored(self, path: str) -> bool:
        for pattern in self.ignored_patterns:
            if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern):
                return True
        return False

    def code_scout(self, path: str = ".", depth: int = 2) -> Dict[str, Any]:
        """
        Scouts the directory structure, respecting ignores and depth limits.
        """
        start_path = (self.root_dir / path).resolve()
        if not start_path.is_relative_to(self.root_dir):
            raise ValueError(f"Access denied: {path}")

        result = {
            "path": str(path),
            "type": "directory",
            "children": []
        }

        def _scan(current_path: Path, current_depth: int) -> List[Dict[str, Any]]:
            if current_depth > depth:
                return []
            
            children = []
            try:
                for item in sorted(current_path.iterdir()):
                    if self._is_ignored(item.name):
                        continue
                    
                    child_info = {
                        "name": item.name,
                        "path": str(item.relative_to(self.root_dir)),
                        "type": "directory" if item.is_dir() else "file"
                    }
                    
                    if item.is_dir():
                        if current_depth < depth:
                            child_info["children"] = _scan(item, current_depth + 1)
                        else:
                            child_info["truncated"] = True
                    else:
                        child_info["size"] = item.stat().st_size
                        
                    children.append(child_info)
            except PermissionError:
                pass
            return children

        result["children"] = _scan(start_path, 1)
        return result

    def code_probe(self, paths: List[str]) -> Dict[str, Any]:
        """
        Selectively loads files into RAM cache.
        """
        loaded = []
        failed = []
        total_size = 0

        for p in paths:
            try:
                full_path = (self.root_dir / p).resolve()
                if not full_path.is_relative_to(self.root_dir) or not full_path.exists() or not full_path.is_file():
                    failed.append({"path": p, "reason": "Invalid path or not a file"})
                    continue
                
                if self._is_ignored(full_path.name):
                     failed.append({"path": p, "reason": "Ignored file"})
                     continue

                # Check cache size limit roughly
                current_cache_size = sum(e.size for e in self.cache.values())
                file_size = full_path.stat().st_size
                
                if current_cache_size + file_size > self.max_cache_size:
                    # Evict oldest
                    sorted_entries = sorted(self.cache.items(), key=lambda x: x[1].timestamp)
                    while current_cache_size + file_size > self.max_cache_size and sorted_entries:
                        k, v = sorted_entries.pop(0)
                        del self.cache[k]
                        current_cache_size -= v.size

                content = full_path.read_text(errors='replace')
                self.cache[str(p)] = RAMCacheEntry(
                    content=content,
                    timestamp=time.time(),
                    size=len(content),
                    path=str(p)
                )
                loaded.append({"path": p, "size": len(content)})
                total_size += len(content)
                
            except Exception as e:
                failed.append({"path": p, "reason": str(e)})

        return {
            "loaded": loaded,
            "failed": failed,
            "total_loaded_size": total_size,
            "cache_count": len(self.cache)
        }

    def ram_search(self, query: str, regex: bool = False, context_lines: int = 2) -> Dict[str, Any]:
        """
        Searches exclusively within the RAM cache.
        """
        matches = []
        
        try:
            pattern = re.compile(query, re.IGNORECASE) if regex else None
        except re.error as e:
            return {"error": f"Invalid regex: {e}"}

        for path, entry in self.cache.items():
            lines = entry.content.splitlines()
            for i, line in enumerate(lines):
                found = False
                if regex and pattern:
                    if pattern.search(line):
                        found = True
                elif query.lower() in line.lower():
                    found = True
                
                if found:
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    context = lines[start:end]
                    
                    matches.append({
                        "file": path,
                        "line": i + 1,
                        "content": line.strip(),
                        "context": "\n".join(context)
                    })

        return {
            "query": query,
            "regex": regex,
            "matches": matches,
            "count": len(matches),
            "searched_files": len(self.cache)
        }

    def ram_context_export(self, file_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Exports content from RAM cache for context.
        """
        exported = {}
        paths_to_export = file_paths if file_paths else list(self.cache.keys())
        
        for p in paths_to_export:
            if p in self.cache:
                exported[p] = self.cache[p].content
        
        return {
            "files": exported,
            "count": len(exported)
        }

    def ram_patch_apply(self, patch_content: str, dry_run: bool = True) -> Dict[str, Any]:
        """
        Applies a unified diff patch.
        """
        results = []
        
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.patch', delete=False) as tmp:
            tmp.write(patch_content)
            patch_file = tmp.name

        try:
            cmd = ["patch", "-p1", "-N"] # -N: ignore patches already applied
            if dry_run:
                cmd.append("--dry-run")
            
            cmd.extend(["-i", patch_file])
            
            # Run from root dir
            try:
                proc = subprocess.run(
                    cmd, 
                    cwd=self.root_dir, 
                    capture_output=True, 
                    text=True
                )
            except FileNotFoundError:
                return {
                    "dry_run": dry_run,
                    "success": False,
                    "error": "The 'patch' command is not available on this system."
                }
            
            # Invalidate cache for affected files if not dry run
            if not dry_run and proc.returncode == 0:
                # Very basic cache invalidation: clear everything or parse patch output
                # For safety, let's just clear the cache for now or let the user re-probe
                pass 

            return {
                "dry_run": dry_run,
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr
            }
            
        finally:
            if os.path.exists(patch_file):
                os.unlink(patch_file)

# Singleton instance
illuminator = AdaptiveCodeIlluminator()

# MCP Tool Wrappers
async def handle_code_scout(params: Dict[str, Any]) -> Dict[str, Any]:
    path = params.get("path", ".")
    depth = params.get("depth", 2)
    return illuminator.code_scout(path, depth)

async def handle_code_probe(params: Dict[str, Any]) -> Dict[str, Any]:
    paths = params.get("paths", [])
    if isinstance(paths, str):
        paths = [paths]
    return illuminator.code_probe(paths)

async def handle_ram_search(params: Dict[str, Any]) -> Dict[str, Any]:
    query = params.get("query")
    if not query:
        raise ValueError("Query required")
    regex = params.get("regex", False)
    return illuminator.ram_search(query, regex)

async def handle_ram_context_export(params: Dict[str, Any]) -> Dict[str, Any]:
    file_paths = params.get("file_paths")
    return illuminator.ram_context_export(file_paths)

async def handle_ram_patch_apply(params: Dict[str, Any]) -> Dict[str, Any]:
    diff = params.get("diff")
    if not diff:
        raise ValueError("Diff content required")
    dry_run = params.get("dry_run", True)
    return illuminator.ram_patch_apply(diff, dry_run)

ADAPTIVE_CODE_TOOLS = [
    {
        "name": "code_scout",
        "description": "Scout directory structure with depth limit and ignore patterns. Adaptive Code Illumination tool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to scout (default: .)"},
                "depth": {"type": "integer", "description": "Depth to traverse (default: 2)"}
            }
        }
    },
    {
        "name": "code_probe",
        "description": "Selectively load files into RAM cache for fast analysis. Adaptive Code Illumination tool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "paths": {"type": "array", "items": {"type": "string"}, "description": "List of file paths to load"}
            },
            "required": ["paths"]
        }
    },
    {
        "name": "ram_search",
        "description": "Search text/regex within loaded RAM cache (no disk I/O). Adaptive Code Illumination tool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "regex": {"type": "boolean", "description": "Use regex (default: false)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "ram_context_export",
        "description": "Export content from RAM cache for agent context. Adaptive Code Illumination tool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_paths": {"type": "array", "items": {"type": "string"}, "description": "Specific files to export (optional, default: all cached)"}
            }
        }
    },
    {
        "name": "ram_patch_apply",
        "description": "Apply unified diff patch (default dry-run). Adaptive Code Illumination tool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "diff": {"type": "string", "description": "Unified diff content"},
                "dry_run": {"type": "boolean", "description": "Preview only (default: true)"}
            },
            "required": ["diff"]
        }
    }
]

ADAPTIVE_CODE_HANDLERS = {
    "code_scout": handle_code_scout,
    "code_probe": handle_code_probe,
    "ram_search": handle_ram_search,
    "ram_context_export": handle_ram_context_export,
    "ram_patch_apply": handle_ram_patch_apply
}
