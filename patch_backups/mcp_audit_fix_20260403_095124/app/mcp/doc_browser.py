"""
MCP Doc-Browser Tool v1.0
==========================
Rekursiver Dokumentations-Browser für das TriForce-Projekt.

Funktionen:
  doc_scan    - Rekursiv alle *.md, *.txt, *.json, *.sh, *.py Dateien finden
  doc_read    - Datei lesen mit Metadaten (Zeilen, Größe, Modified)
  doc_search  - Volltext-Suche über alle Dateien (grep-style + Kontext)
  doc_tree    - Verzeichnis-Tree nur für Dok-Dateien
  doc_stats   - Statistik über die gesamte Doku-Basis

Autor: Nova / Markus Leitermann
Datum: 2026-03-11
"""

import os
import re
import json
import fnmatch
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ailinux.mcp.docbrowser")

PROJECT_ROOT = Path("/home/zombie/triforce")

# Dateitypen die der Browser kennt
DOC_EXTENSIONS = {
    ".md":   "markdown",
    ".txt":  "text",
    ".rst":  "restructuredtext",
    ".json": "json",
    ".sh":   "shell",
    ".env":  "env",
    ".yml":  "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".cfg":  "config",
    ".ini":  "config",
    ".tf":   "terraform",
}

# Verzeichnisse die wir überspringen
SKIP_DIRS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache",
    "node_modules", ".backups", ".repair-backup", ".debug",
    "logs", "certs", "build", ".claude"
}

# Dateien die wir überspringen (zu groß / irrelevant)
SKIP_PATTERNS = [
    "*.log", "*.pid", "*.sock", "*.pyc",
    "all-debug-*", "all-combined-*", "all-error-*", "gather.log",
    "mcp_write_lock_debug*"
]


def _should_skip_file(filename: str) -> bool:
    return any(fnmatch.fnmatch(filename, p) for p in SKIP_PATTERNS)


def _get_file_meta(path: Path) -> Dict[str, Any]:
    """Metadaten einer Datei sammeln."""
    try:
        stat = path.stat()
        size = stat.st_size
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        ext = path.suffix.lower()
        kind = DOC_EXTENSIONS.get(ext, "unknown")

        # Zeilenzahl für Textdateien
        lines = None
        if size < 2_000_000 and kind != "unknown":
            try:
                lines = sum(1 for _ in path.open("r", errors="replace"))
            except Exception:
                pass

        rel = str(path.relative_to(PROJECT_ROOT))
        return {
            "path": str(path),
            "rel_path": rel,
            "name": path.name,
            "ext": ext,
            "kind": kind,
            "size_bytes": size,
            "size_human": _human_size(size),
            "modified": modified,
            "lines": lines,
            "dir": str(path.parent.relative_to(PROJECT_ROOT)),
        }
    except Exception as e:
        return {"path": str(path), "error": str(e)}


def _human_size(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def _collect_files(
    root: Path,
    extensions: List[str],
    max_depth: Optional[int] = None,
    current_depth: int = 0
) -> List[Path]:
    """Rekursiv Dateien sammeln."""
    results = []
    if max_depth is not None and current_depth > max_depth:
        return results

    try:
        entries = sorted(root.iterdir())
    except PermissionError:
        return results

    for entry in entries:
        if entry.is_dir():
            if entry.name in SKIP_DIRS or entry.name.startswith("."):
                continue
            results += _collect_files(entry, extensions, max_depth, current_depth + 1)
        elif entry.is_file():
            if _should_skip_file(entry.name):
                continue
            if entry.suffix.lower() in extensions or entry.name in extensions:
                results.append(entry)

    return results


# =============================================================================
# HANDLER: doc_scan
# =============================================================================

async def handle_doc_scan(params: Dict[str, Any]) -> Dict[str, Any]:
    """Rekursiv alle Dokumentationsdateien finden."""
    base_path = params.get("path", str(PROJECT_ROOT))
    ext_filter = params.get("extensions", [".md", ".txt", ".sh", ".json"])
    max_depth = params.get("max_depth", None)
    sort_by = params.get("sort_by", "rel_path")  # rel_path | modified | size | kind
    category_filter = params.get("category", None)  # docs | scripts | config | all

    root = Path(base_path)
    if not root.exists():
        return {"error": f"Pfad nicht gefunden: {base_path}"}

    # Extension-Filter normalisieren
    exts = [e if e.startswith(".") else f".{e}" for e in ext_filter]

    # Kategorie-Shortcuts
    if category_filter == "docs":
        exts = [".md", ".txt", ".rst"]
    elif category_filter == "scripts":
        exts = [".sh", ".bash"]
    elif category_filter == "config":
        exts = [".json", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".env", ".tf"]
    elif category_filter == "all":
        exts = list(DOC_EXTENSIONS.keys())

    files = _collect_files(root, exts, max_depth)
    metas = [_get_file_meta(f) for f in files]

    # Sortierung
    sort_keys = {
        "rel_path": lambda x: x.get("rel_path", ""),
        "modified": lambda x: x.get("modified", ""),
        "size": lambda x: x.get("size_bytes", 0),
        "kind": lambda x: (x.get("kind", ""), x.get("rel_path", "")),
        "name": lambda x: x.get("name", ""),
    }
    key_fn = sort_keys.get(sort_by, sort_keys["rel_path"])
    metas.sort(key=key_fn)

    # Zusammenfassung
    total_size = sum(m.get("size_bytes", 0) for m in metas)
    by_kind: Dict[str, int] = {}
    for m in metas:
        k = m.get("kind", "unknown")
        by_kind[k] = by_kind.get(k, 0) + 1

    return {
        "count": len(metas),
        "total_size": _human_size(total_size),
        "by_kind": by_kind,
        "extensions_scanned": exts,
        "base_path": str(root.relative_to(PROJECT_ROOT) if root != PROJECT_ROOT else "."),
        "files": metas,
    }


# =============================================================================
# HANDLER: doc_read
# =============================================================================

async def handle_doc_read(params: Dict[str, Any]) -> Dict[str, Any]:
    """Datei lesen mit Metadaten und optionalem Zeilenfenster."""
    path = params.get("path", "")
    start_line = params.get("start_line", 1)
    end_line = params.get("end_line", None)
    show_meta = params.get("show_meta", True)
    max_chars = params.get("max_chars", 50_000)

    if not path:
        return {"error": "path ist erforderlich"}

    abs_path = Path(path) if path.startswith("/") else PROJECT_ROOT / path
    if not abs_path.exists():
        return {"error": f"Datei nicht gefunden: {path}"}

    meta = _get_file_meta(abs_path)

    try:
        with abs_path.open("r", errors="replace") as f:
            all_lines = f.readlines()

        total_lines = len(all_lines)

        # Zeilenfenster
        s = max(0, start_line - 1)
        e = end_line if end_line else total_lines
        selected = all_lines[s:e]
        content = "".join(selected)

        # Zeichenlimit
        truncated = False
        if len(content) > max_chars:
            content = content[:max_chars]
            truncated = True

        result: Dict[str, Any] = {
            "content": content,
            "total_lines": total_lines,
            "shown_lines": f"{s+1}–{min(e, total_lines)}",
            "truncated": truncated,
        }
        if show_meta:
            result["meta"] = meta

        return result

    except Exception as e:
        return {"error": str(e), "meta": meta}


# =============================================================================
# HANDLER: doc_search
# =============================================================================

async def handle_doc_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Volltext-Suche über Dokumentationsdateien."""
    query = params.get("query", "")
    extensions = params.get("extensions", [".md", ".txt", ".sh", ".json", ".py"])
    base_path = params.get("path", str(PROJECT_ROOT))
    max_results = params.get("max_results", 50)
    context_lines = params.get("context_lines", 2)
    case_sensitive = params.get("case_sensitive", False)
    regex_mode = params.get("regex", False)

    if not query:
        return {"error": "query ist erforderlich"}

    root = Path(base_path)
    exts = [e if e.startswith(".") else f".{e}" for e in extensions]
    files = _collect_files(root, exts)

    # Pattern kompilieren
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        if regex_mode:
            pattern = re.compile(query, flags)
        else:
            pattern = re.compile(re.escape(query), flags)
    except re.error as e:
        return {"error": f"Ungültiges Regex: {e}"}

    results = []
    files_searched = 0
    files_with_matches = 0

    for fpath in files:
        if len(results) >= max_results:
            break
        try:
            with fpath.open("r", errors="replace") as f:
                lines = f.readlines()
            files_searched += 1

            file_matches = []
            for i, line in enumerate(lines):
                if pattern.search(line):
                    # Kontext-Zeilen sammeln
                    ctx_start = max(0, i - context_lines)
                    ctx_end = min(len(lines), i + context_lines + 1)
                    context = []
                    for j in range(ctx_start, ctx_end):
                        marker = ">>> " if j == i else "    "
                        context.append(f"{marker}{j+1:4d}: {lines[j].rstrip()}")

                    file_matches.append({
                        "line": i + 1,
                        "text": line.strip(),
                        "context": "\n".join(context),
                    })

            if file_matches:
                files_with_matches += 1
                results.append({
                    "file": str(fpath.relative_to(PROJECT_ROOT)),
                    "matches": file_matches,
                    "match_count": len(file_matches),
                })

        except Exception:
            continue

    total_matches = sum(r["match_count"] for r in results)

    return {
        "query": query,
        "total_matches": total_matches,
        "files_with_matches": files_with_matches,
        "files_searched": files_searched,
        "results": results,
    }


# =============================================================================
# HANDLER: doc_tree
# =============================================================================

async def handle_doc_tree(params: Dict[str, Any]) -> Dict[str, Any]:
    """Verzeichnis-Tree für Dokumentationsdateien."""
    base_path = params.get("path", str(PROJECT_ROOT))
    extensions = params.get("extensions", [".md", ".txt", ".sh"])
    max_depth = params.get("max_depth", 4)

    root = Path(base_path)
    exts = [e if e.startswith(".") else f".{e}" for e in extensions]

    def build_tree(path: Path, depth: int = 0) -> Optional[Dict]:
        if max_depth is not None and depth > max_depth:
            return None
        if path.name in SKIP_DIRS or path.name.startswith("."):
            return None

        if path.is_file():
            if path.suffix.lower() not in exts:
                return None
            if _should_skip_file(path.name):
                return None
            stat = path.stat()
            return {
                "type": "file",
                "name": path.name,
                "size": _human_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
                "kind": DOC_EXTENSIONS.get(path.suffix.lower(), "?"),
            }

        # Directory
        children = []
        try:
            for entry in sorted(path.iterdir()):
                node = build_tree(entry, depth + 1)
                if node:
                    children.append(node)
        except PermissionError:
            pass

        if not children:
            return None

        return {
            "type": "dir",
            "name": path.name,
            "children": children,
            "count": sum(1 for c in children if c["type"] == "file"),
        }

    tree = build_tree(root)

    # Als Text-Tree rendern
    def render(node: Dict, prefix: str = "", is_last: bool = True) -> List[str]:
        if not node:
            return []
        connector = "└── " if is_last else "├── "
        lines = []
        if node["type"] == "dir":
            lines.append(f"{prefix}{connector}📁 {node['name']}/ ({node.get('count',0)} files)")
            new_prefix = prefix + ("    " if is_last else "│   ")
            children = node.get("children", [])
            for i, child in enumerate(children):
                lines += render(child, new_prefix, i == len(children) - 1)
        else:
            icon = {"markdown": "📄", "shell": "⚙️", "text": "📃", "json": "🔧"}.get(node["kind"], "📄")
            lines.append(f"{prefix}{connector}{icon} {node['name']} [{node['size']}] {node['modified']}")
        return lines

    lines = [f"📂 {root.name}/"] + render(tree, "", True)[1:]

    return {
        "tree": "\n".join(lines),
        "base": str(root.relative_to(PROJECT_ROOT) if root != PROJECT_ROOT else "."),
    }


# =============================================================================
# HANDLER: doc_stats
# =============================================================================

async def handle_doc_stats(params: Dict[str, Any]) -> Dict[str, Any]:
    """Statistik über die gesamte Dokumentationsbasis."""
    base_path = params.get("path", str(PROJECT_ROOT))
    root = Path(base_path)

    all_exts = list(DOC_EXTENSIONS.keys())
    files = _collect_files(root, all_exts)

    total_size = 0
    total_lines = 0
    by_ext: Dict[str, Dict] = {}
    newest = None
    oldest = None

    for fpath in files:
        try:
            stat = fpath.stat()
            size = stat.st_size
            mtime = stat.st_mtime
            total_size += size

            ext = fpath.suffix.lower()
            if ext not in by_ext:
                by_ext[ext] = {"count": 0, "size": 0, "lines": 0}
            by_ext[ext]["count"] += 1
            by_ext[ext]["size"] += size

            if size < 1_000_000:
                try:
                    lc = sum(1 for _ in fpath.open("r", errors="replace"))
                    total_lines += lc
                    by_ext[ext]["lines"] += lc
                except Exception:
                    pass

            if newest is None or mtime > newest[1]:
                newest = (str(fpath.relative_to(PROJECT_ROOT)), mtime)
            if oldest is None or mtime < oldest[1]:
                oldest = (str(fpath.relative_to(PROJECT_ROOT)), mtime)

        except Exception:
            continue

    # Top 10 größte Dateien
    metas = sorted(
        [_get_file_meta(f) for f in files],
        key=lambda x: x.get("size_bytes", 0),
        reverse=True
    )[:10]

    return {
        "total_files": len(files),
        "total_size": _human_size(total_size),
        "total_lines": total_lines,
        "by_extension": {
            ext: {
                "count": v["count"],
                "size": _human_size(v["size"]),
                "lines": v["lines"],
            }
            for ext, v in sorted(by_ext.items(), key=lambda x: -x[1]["count"])
        },
        "newest_file": {
            "path": newest[0],
            "modified": datetime.fromtimestamp(newest[1]).strftime("%Y-%m-%d %H:%M")
        } if newest else None,
        "oldest_file": {
            "path": oldest[0],
            "modified": datetime.fromtimestamp(oldest[1]).strftime("%Y-%m-%d %H:%M")
        } if oldest else None,
        "largest_files": [
            {"path": m["rel_path"], "size": m["size_human"], "lines": m.get("lines")}
            for m in metas
        ],
    }


# =============================================================================
# HANDLER REGISTRY
# =============================================================================

DOC_TOOL_HANDLERS = {
    "doc_scan":   handle_doc_scan,
    "doc_read":   handle_doc_read,
    "doc_search": handle_doc_search,
    "doc_tree":   handle_doc_tree,
    "doc_stats":  handle_doc_stats,
}

DOC_TOOL_NAMES = list(DOC_TOOL_HANDLERS.keys())
