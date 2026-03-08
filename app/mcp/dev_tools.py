"""
MCP Dev-Tools Handlers v5.0
============================
KI-optimierte Entwickler-Tools:
  dev_analyze   - Bug/Typo/Security/DeadCode detection
  dev_lint      - Syntax+Style für alle Sprachen
  dev_debug     - Auto-Debugger mit Root-Cause Analysis
  dev_summarize - Code-Zusammenfassung für AI-Kontext
  dev_links     - Broken import/reference detection
  dev_refactor  - AI-powered Refactoring-Vorschläge
  git           - Unified git operations
"""

import os
import re
import ast
import json
import subprocess
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ailinux.mcp.devtools")

PROJECT_ROOT = Path("/home/zombie/triforce")


def _run(cmd: str, cwd: str = None, timeout: int = 30) -> Dict[str, Any]:
    """Run shell command, return stdout/stderr/exit_code."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=cwd or str(PROJECT_ROOT)
        )
        return {"stdout": r.stdout, "stderr": r.stderr, "exit_code": r.returncode}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Timeout after {timeout}s", "exit_code": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": -1}


def _detect_language(path: str) -> str:
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".sh": "bash", ".bash": "bash", ".zsh": "bash",
        ".go": "go", ".rs": "rust", ".php": "php",
        ".rb": "ruby", ".java": "java", ".c": "c", ".cpp": "cpp",
        ".cs": "csharp", ".kt": "kotlin", ".swift": "swift",
    }
    ext = Path(path).suffix.lower()
    return ext_map.get(ext, "unknown")


# =============================================================================
# dev_analyze — AI-powered Code Analysis
# =============================================================================

async def handle_dev_analyze(params: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse code: bugs, typos, security, dead code, complexity."""
    path = params.get("path", "")
    checks = params.get("checks", ["all"])
    severity_filter = params.get("severity", "warning")
    language = params.get("language") or _detect_language(path)

    if not path:
        return {"error": "path is required"}

    abs_path = path if path.startswith("/") else str(PROJECT_ROOT / path)
    if not os.path.exists(abs_path):
        return {"error": f"Path not found: {abs_path}"}

    issues = []
    severity_levels = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    min_sev = severity_levels.get(severity_filter, 1)

    # --- Python specific analysis ---
    if language == "python" or (language == "unknown" and abs_path.endswith(".py")):
        issues += _analyze_python(abs_path, checks)

    # --- Bash analysis ---
    elif language == "bash":
        issues += _analyze_bash(abs_path)

    # --- Generic analysis (all languages) ---
    issues += _analyze_generic(abs_path, checks)

    # Filter by severity
    filtered = [i for i in issues if severity_levels.get(i.get("severity", "info"), 0) >= min_sev]
    filtered.sort(key=lambda x: (-severity_levels.get(x.get("severity","info"),0), x.get("line",0)))

    return {
        "path": abs_path,
        "language": language,
        "issues_found": len(filtered),
        "issues": filtered[:100],
        "summary": {
            "critical": len([i for i in filtered if i.get("severity") == "critical"]),
            "error": len([i for i in filtered if i.get("severity") == "error"]),
            "warning": len([i for i in filtered if i.get("severity") == "warning"]),
            "info": len([i for i in filtered if i.get("severity") == "info"]),
        }
    }


def _analyze_python(path: str, checks: List[str]) -> List[Dict]:
    issues = []
    do_all = "all" in checks

    # ruff for fast linting
    r = _run(f"python3 -m ruff check --output-format json '{path}' 2>/dev/null || ruff check --output-format json '{path}' 2>/dev/null")
    if r["stdout"]:
        try:
            ruff_issues = json.loads(r["stdout"])
            for issue in ruff_issues[:50]:
                issues.append({
                    "file": issue.get("filename", path),
                    "line": issue.get("location", {}).get("row", 0),
                    "col": issue.get("location", {}).get("column", 0),
                    "severity": "error" if issue.get("code","").startswith("E") else "warning",
                    "code": issue.get("code", ""),
                    "message": issue.get("message", ""),
                    "category": "lint",
                })
        except (json.JSONDecodeError, Exception):
            pass

    # AST-based analysis for typos in identifiers
    if do_all or "typos" in checks:
        try:
            content = Path(path).read_text(errors='replace') if os.path.isfile(path) else ""
            tree = ast.parse(content)
            common_typos = {
                "lenght": "length", "widht": "width", "heigth": "height",
                "recieve": "receive", "occured": "occurred", "seperator": "separator",
                "paramter": "parameter", "paremeter": "parameter", "retrun": "return",
                "funciton": "function", "functoin": "function", "resposne": "response",
                "requets": "request", "databse": "database", "conncetion": "connection",
                "authetication": "authentication", "authorizaiton": "authorization",
                "configuraiton": "configuration", "configuraion": "configuration",
            }
            for node in ast.walk(tree):
                name = None
                line = getattr(node, 'lineno', 0)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    name = node.name
                elif isinstance(node, ast.Name):
                    name = node.id
                elif isinstance(node, ast.Attribute):
                    name = node.attr
                if name:
                    for typo, correct in common_typos.items():
                        if typo in name.lower():
                            issues.append({
                                "file": path, "line": line,
                                "severity": "warning",
                                "code": "TYPO",
                                "message": f"Possible typo '{name}' — did you mean '{name.lower().replace(typo, correct)}'?",
                                "category": "typo",
                            })
        except SyntaxError:
            pass

    # Security checks
    if do_all or "security" in checks:
        content = Path(path).read_text(errors='replace') if os.path.isfile(path) else ""
        sec_patterns = [
            (r'(password|passwd|secret|api_key|token)\s*=\s*["\'][^"\']{4,}["\']', "Hardcoded credential", "critical"),
            (r'eval\s*\(', "Use of eval() - potential code injection", "error"),
            (r'exec\s*\(', "Use of exec() - potential code injection", "error"),
            (r'subprocess.*shell\s*=\s*True', "shell=True in subprocess - injection risk", "warning"),
            (r'pickle\.loads?\s*\(', "Pickle deserialization - security risk", "warning"),
            (r'os\.system\s*\(', "os.system() - use subprocess instead", "warning"),
        ]
        for i, line in enumerate(content.splitlines(), 1):
            for pattern, msg, sev in sec_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        "file": path, "line": i,
                        "severity": sev,
                        "code": "SEC",
                        "message": msg,
                        "category": "security",
                    })

    return issues


def _analyze_bash(path: str) -> List[Dict]:
    issues = []
    r = _run(f"shellcheck -f json '{path}' 2>/dev/null")
    if r["stdout"]:
        try:
            sc = json.loads(r["stdout"])
            for item in sc[:30]:
                issues.append({
                    "file": item.get("file", path),
                    "line": item.get("line", 0),
                    "col": item.get("column", 0),
                    "severity": item.get("level", "warning"),
                    "code": f"SC{item.get('code','')}",
                    "message": item.get("message", ""),
                    "category": "lint",
                })
        except (json.JSONDecodeError, Exception):
            pass
    return issues


def _analyze_generic(path: str, checks: List[str]) -> List[Dict]:
    issues = []
    do_all = "all" in checks
    if not os.path.isfile(path):
        return issues
    try:
        content = Path(path).read_text(errors='replace')
        lines = content.splitlines()
    except Exception:
        return issues

    # TODO/FIXME/HACK detection
    if do_all or "dead_code" in checks:
        markers = [("TODO", "info"), ("FIXME", "warning"), ("HACK", "warning"),
                   ("XXX", "warning"), ("BUG", "error"), ("NOQA", "info")]
        for i, line in enumerate(lines, 1):
            for marker, sev in markers:
                if marker in line:
                    issues.append({
                        "file": path, "line": i,
                        "severity": sev,
                        "code": marker,
                        "message": f"{marker} comment: {line.strip()[:80]}",
                        "category": "code_quality",
                    })

    # Long lines
    for i, line in enumerate(lines, 1):
        if len(line) > 200:
            issues.append({
                "file": path, "line": i,
                "severity": "info",
                "code": "LONGLINE",
                "message": f"Line too long ({len(line)} chars)",
                "category": "style",
            })

    return issues


# =============================================================================
# dev_lint — Multi-language Linter
# =============================================================================

async def handle_dev_lint(params: Dict[str, Any]) -> Dict[str, Any]:
    path = params.get("path", "")
    language = params.get("language", "auto")
    fix = params.get("fix", False)

    if not path:
        return {"error": "path is required"}

    abs_path = path if path.startswith("/") else str(PROJECT_ROOT / path)
    if language == "auto":
        language = _detect_language(abs_path)

    results = {"path": abs_path, "language": language, "errors": [], "warnings": [], "fixed": []}

    if language == "python":
        fix_flag = "--fix" if fix else ""
        r = _run(f"python3 -m ruff check {fix_flag} --output-format json '{abs_path}' 2>/dev/null")
        if r["stdout"]:
            try:
                items = json.loads(r["stdout"])
                for item in items:
                    entry = {
                        "file": item.get("filename"),
                        "line": item.get("location", {}).get("row"),
                        "col": item.get("location", {}).get("column"),
                        "code": item.get("code"),
                        "message": item.get("message"),
                    }
                    if item.get("code", "").startswith("E"):
                        results["errors"].append(entry)
                    else:
                        results["warnings"].append(entry)
            except (json.JSONDecodeError, Exception):
                results["raw"] = r["stdout"][:500]

        # mypy type check
        r2 = _run(f"python3 -m mypy --ignore-missing-imports --no-error-summary '{abs_path}' 2>/dev/null")
        for line in r2["stdout"].splitlines():
            if ": error:" in line:
                parts = line.split(":")
                results["errors"].append({"file": parts[0] if parts else abs_path, "message": line.strip()})

    elif language == "bash":
        r = _run(f"shellcheck -f gcc '{abs_path}' 2>/dev/null")
        for line in r["stdout"].splitlines():
            entry = {"file": abs_path, "message": line.strip()}
            if "error" in line.lower():
                results["errors"].append(entry)
            else:
                results["warnings"].append(entry)

    elif language in ("javascript", "typescript"):
        r = _run(f"npx eslint --format json '{abs_path}' 2>/dev/null")
        if r["stdout"]:
            try:
                items = json.loads(r["stdout"])
                for file_result in items:
                    for msg in file_result.get("messages", []):
                        entry = {
                            "file": file_result.get("filePath"),
                            "line": msg.get("line"),
                            "col": msg.get("column"),
                            "code": msg.get("ruleId"),
                            "message": msg.get("message"),
                        }
                        if msg.get("severity") == 2:
                            results["errors"].append(entry)
                        else:
                            results["warnings"].append(entry)
            except (json.JSONDecodeError, Exception):
                results["raw"] = r["stdout"][:500]

    elif language == "go":
        r = _run(f"golint '{abs_path}' 2>/dev/null")
        for line in r["stdout"].splitlines():
            results["warnings"].append({"file": abs_path, "message": line.strip()})

    elif language == "rust":
        r = _run(f"cargo clippy --message-format json 2>/dev/null", cwd=str(Path(abs_path).parent))
        results["raw"] = r["stdout"][:1000]

    results["total_errors"] = len(results["errors"])
    results["total_warnings"] = len(results["warnings"])
    results["clean"] = results["total_errors"] == 0 and results["total_warnings"] == 0
    return results


# =============================================================================
# dev_debug — Auto-Debugger
# =============================================================================

async def handle_dev_debug(params: Dict[str, Any]) -> Dict[str, Any]:
    error = params.get("error", "")
    file_path = params.get("file")
    context = params.get("context", "")

    if not error:
        return {"error": "error message is required"}

    analysis = {
        "error_type": None,
        "root_cause": None,
        "file": None,
        "line": None,
        "fix_suggestions": [],
        "code_context": None,
    }

    # Extract error type and location
    # Python traceback pattern
    tb_match = re.search(r'File "([^"]+)", line (\d+)', error)
    if tb_match:
        analysis["file"] = tb_match.group(1)
        analysis["line"] = int(tb_match.group(2))

    # Error type
    err_match = re.search(r'(\w+Error|\w+Exception|Traceback)', error)
    if err_match:
        analysis["error_type"] = err_match.group(1)

    # Common error patterns → fix suggestions
    error_patterns = [
        (r"ModuleNotFoundError.*'([^']+)'", lambda m: f"Install missing module: pip install {m.group(1)}"),
        (r"ImportError.*cannot import name '([^']+)'.*from '([^']+)'",
         lambda m: f"'{m.group(1)}' not in '{m.group(2)}' — check module version or typo"),
        (r"AttributeError.*'(\w+)'.*has no attribute '([^']+)'",
         lambda m: f"'{m.group(2)}' not on {m.group(1)} — check spelling or object type"),
        (r"TypeError.*takes (\d+) positional argument.*(\d+) (were|was) given",
         lambda m: f"Wrong argument count — expected {m.group(1)}, got {m.group(2)}"),
        (r"KeyError.*'([^']+)'", lambda m: f"Key '{m.group(1)}' missing — use .get() or check dict contents"),
        (r"IndexError.*list index out of range",
         lambda m: "List index out of range — check loop bounds or list length before access"),
        (r"FileNotFoundError.*'([^']+)'", lambda m: f"File not found: {m.group(1)} — check path exists"),
        (r"PermissionError", lambda m: "Permission denied — check file permissions or use sudo"),
        (r"ConnectionRefusedError", lambda m: "Connection refused — check if service is running and port is correct"),
        (r"JSONDecodeError", lambda m: "Invalid JSON — validate input with json.loads() in try/except"),
        (r"SyntaxError.*invalid syntax", lambda m: "Syntax error — check for missing colons, brackets, or quotes"),
        (r"IndentationError", lambda m: "Indentation error — check for mixed tabs/spaces"),
        (r"RecursionError", lambda m: "Max recursion reached — add base case or use iterative approach"),
        (r"MemoryError", lambda m: "Out of memory — process data in chunks or optimize data structures"),
        (r"TimeoutError|timeout", lambda m: "Timeout — increase timeout value or optimize the slow operation"),
        (r"UnicodeDecodeError.*codec.*'([^']+)'",
         lambda m: f"Encoding error with codec '{m.group(1)}' — use errors='replace' or specify encoding='utf-8'"),
    ]

    for pattern, suggestion_fn in error_patterns:
        m = re.search(pattern, error, re.IGNORECASE)
        if m:
            try:
                analysis["fix_suggestions"].append(suggestion_fn(m))
            except Exception:
                pass

    # Read code context if file provided
    if file_path or analysis["file"]:
        target = file_path or analysis["file"]
        if os.path.exists(target) and analysis["line"]:
            try:
                lines = Path(target).read_text(errors='replace').splitlines()
                line_num = analysis["line"]
                start = max(0, line_num - 5)
                end = min(len(lines), line_num + 5)
                analysis["code_context"] = "\n".join(
                    f"{'>>>' if i+1 == line_num else '   '} {i+start+1:4d}: {lines[i+start]}"
                    for i in range(end - start)
                )
            except Exception:
                pass

    # Root cause determination
    if analysis["error_type"] == "ModuleNotFoundError":
        analysis["root_cause"] = "Missing Python dependency"
    elif analysis["error_type"] == "AttributeError":
        analysis["root_cause"] = "Wrong type or typo in attribute/method name"
    elif analysis["error_type"] == "TypeError":
        analysis["root_cause"] = "Type mismatch or wrong number of arguments"
    elif analysis["error_type"] == "KeyError":
        analysis["root_cause"] = "Dictionary key does not exist"
    elif analysis["error_type"] == "SyntaxError":
        analysis["root_cause"] = "Python syntax error in source code"
    elif "permission" in error.lower():
        analysis["root_cause"] = "Insufficient file/process permissions"
    elif "connection" in error.lower():
        analysis["root_cause"] = "Network or service connectivity issue"
    else:
        analysis["root_cause"] = "See fix suggestions for details"

    if not analysis["fix_suggestions"]:
        analysis["fix_suggestions"].append("No automatic fix found — provide more error context or the source file path")

    return analysis


# =============================================================================
# dev_summarize — Code Summarizer
# =============================================================================

async def handle_dev_summarize(params: Dict[str, Any]) -> Dict[str, Any]:
    path = params.get("path", "")
    depth = params.get("depth", "normal")
    focus = params.get("focus", "all")

    abs_path = path if path.startswith("/") else str(PROJECT_ROOT / path)
    if not os.path.exists(abs_path):
        return {"error": f"Path not found: {abs_path}"}

    summary = {"path": abs_path, "depth": depth}

    if os.path.isfile(abs_path):
        summary.update(_summarize_file(abs_path, depth, focus))
    else:
        summary.update(_summarize_directory(abs_path, depth, focus))

    return summary


def _summarize_file(path: str, depth: str, focus: str) -> Dict:
    lang = _detect_language(path)
    try:
        content = Path(path).read_text(errors='replace')
    except Exception as e:
        return {"error": str(e)}

    lines = content.splitlines()
    result = {
        "type": "file",
        "language": lang,
        "size_lines": len(lines),
        "size_bytes": os.path.getsize(path),
    }

    if lang == "python":
        try:
            tree = ast.parse(content)
            functions = []
            classes = []
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    doc = ast.get_docstring(node) or ""
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": [a.arg for a in node.args.args],
                        "doc": doc[:80] if doc else None,
                        "async": isinstance(node, ast.AsyncFunctionDef),
                    })
                elif isinstance(node, ast.ClassDef):
                    doc = ast.get_docstring(node) or ""
                    classes.append({"name": node.name, "line": node.lineno, "doc": doc[:80]})
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        imports += [alias.name for alias in node.names]
                    else:
                        imports.append(node.module or "")

            result["functions"] = functions if depth != "brief" else [f["name"] for f in functions]
            result["classes"] = classes if depth != "brief" else [c["name"] for c in classes]
            result["imports"] = list(set(imports))[:20] if focus in ("dependencies", "all") else []
            result["module_docstring"] = ast.get_docstring(tree) or None
        except SyntaxError as e:
            result["parse_error"] = str(e)

    elif lang in ("javascript", "typescript"):
        # Basic JS/TS extraction via regex
        funcs = re.findall(r'(?:function|const|let|var)\s+(\w+)\s*(?:=\s*(?:async\s+)?(?:\([^)]*\)|[^=]+)\s*=>|[=(])', content)
        classes = re.findall(r'class\s+(\w+)', content)
        imports_js = re.findall(r'(?:import|require)\s*[({]?\s*["\']([^"\']+)["\']', content)
        result["functions"] = list(set(funcs))[:30]
        result["classes"] = list(set(classes))
        result["imports"] = list(set(imports_js))[:20]

    return result


def _summarize_directory(path: str, depth: str, focus: str) -> Dict:
    result = {"type": "directory", "structure": {}}
    py_files = list(Path(path).rglob("*.py"))
    js_files = list(Path(path).rglob("*.js")) + list(Path(path).rglob("*.ts"))

    result["file_counts"] = {
        "python": len(py_files),
        "javascript_typescript": len(js_files),
        "total": len(list(Path(path).rglob("*.*"))),
    }

    # Get top-level structure
    tree_r = _run(f"find '{path}' -maxdepth 2 -name '*.py' -o -name '*.js' -o -name '*.ts' | head -40")
    result["key_files"] = [
        str(Path(f).relative_to(path))
        for f in tree_r["stdout"].splitlines() if f
    ]

    # Find entry points
    entry_points = []
    for ep in ["main.py", "app.py", "server.py", "index.js", "index.ts", "manage.py"]:
        if (Path(path) / ep).exists():
            entry_points.append(ep)
    result["entry_points"] = entry_points

    # Find requirements
    for req in ["requirements.txt", "package.json", "pyproject.toml", "Cargo.toml"]:
        if (Path(path) / req).exists():
            result.setdefault("dependency_files", []).append(req)

    return result


# =============================================================================
# dev_links — Broken Reference Finder
# =============================================================================

async def handle_dev_links(params: Dict[str, Any]) -> Dict[str, Any]:
    path = params.get("path", "")
    check_external = params.get("check_external", False)
    language = params.get("language", "auto")

    abs_path = path if path.startswith("/") else str(PROJECT_ROOT / path)
    if not os.path.exists(abs_path):
        return {"error": f"Path not found: {abs_path}"}

    broken = []
    warnings = []

    files = [Path(abs_path)] if os.path.isfile(abs_path) else list(Path(abs_path).rglob("*.py"))[:50]

    for fpath in files:
        lang = _detect_language(str(fpath))
        if lang != "python":
            continue
        try:
            content = fpath.read_text(errors='replace')
            tree = ast.parse(content)
        except (SyntaxError, Exception):
            warnings.append({"file": str(fpath), "message": "Could not parse file (syntax error)"})
            continue

        for node in ast.walk(tree):
            # Check local imports
            if isinstance(node, ast.ImportFrom) and node.module:
                module_path = node.module.replace(".", "/")
                # Relative import check
                if node.level > 0:
                    parent = fpath.parent
                    for _ in range(node.level - 1):
                        parent = parent.parent
                    candidate = parent / (module_path + ".py")
                    candidate_pkg = parent / module_path / "__init__.py"
                    if not candidate.exists() and not candidate_pkg.exists():
                        broken.append({
                            "file": str(fpath.relative_to(abs_path) if abs_path in str(fpath) else fpath),
                            "line": node.lineno,
                            "type": "broken_relative_import",
                            "module": f"{'.' * node.level}{node.module}",
                            "severity": "error",
                        })

            # Check string file paths
            if isinstance(node, ast.Constant) and isinstance(node.s, str):
                val = node.s
                if "/" in val and len(val) > 5 and not val.startswith("http"):
                    candidate = Path(val)
                    if candidate.is_absolute() and not candidate.exists():
                        broken.append({
                            "file": str(fpath),
                            "line": node.lineno,
                            "type": "broken_file_path",
                            "path": val,
                            "severity": "warning",
                        })

    return {
        "path": abs_path,
        "files_scanned": len(files),
        "broken_references": len(broken),
        "issues": broken[:50],
        "warnings": warnings[:10],
    }


# =============================================================================
# dev_refactor — AI-powered Refactoring Suggestions
# =============================================================================

async def handle_dev_refactor(params: Dict[str, Any]) -> Dict[str, Any]:
    path = params.get("path", "")
    focus = params.get("focus", "all")
    apply = params.get("apply", False)

    abs_path = path if path.startswith("/") else str(PROJECT_ROOT / path)
    if not os.path.exists(abs_path):
        return {"error": f"Path not found: {abs_path}"}

    suggestions = []
    lang = _detect_language(abs_path)

    try:
        content = Path(abs_path).read_text(errors='replace')
        lines = content.splitlines()
    except Exception as e:
        return {"error": str(e)}

    if lang == "python":
        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                # Long functions
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_len = (node.end_lineno or node.lineno) - node.lineno
                    if func_len > 50 and (focus in ("structure", "all")):
                        suggestions.append({
                            "type": "extract_function",
                            "severity": "warning",
                            "line": node.lineno,
                            "message": f"Function '{node.name}' is {func_len} lines long — consider splitting into smaller functions",
                            "focus": "structure",
                        })

                    # Too many parameters
                    arg_count = len(node.args.args)
                    if arg_count > 6 and (focus in ("structure", "all")):
                        suggestions.append({
                            "type": "too_many_params",
                            "severity": "warning",
                            "line": node.lineno,
                            "message": f"'{node.name}' has {arg_count} parameters — consider using a dataclass/dict",
                            "focus": "structure",
                        })

                    # Missing type hints
                    has_returns = node.returns is not None
                    has_arg_hints = all(a.annotation is not None for a in node.args.args if a.arg != 'self')
                    if not has_returns and (focus in ("naming", "all")):
                        suggestions.append({
                            "type": "missing_type_hint",
                            "severity": "info",
                            "line": node.lineno,
                            "message": f"'{node.name}' missing return type hint",
                            "focus": "naming",
                        })

                # Nested functions deeper than 2 levels → complexity
                if isinstance(node, ast.For) and (focus in ("performance", "all")):
                    for child in ast.walk(node):
                        if isinstance(child, ast.For) and child is not node:
                            for grandchild in ast.walk(child):
                                if isinstance(grandchild, ast.For) and grandchild is not child:
                                    suggestions.append({
                                        "type": "deep_nesting",
                                        "severity": "warning",
                                        "line": node.lineno,
                                        "message": "Triple-nested loop detected — consider refactoring to reduce complexity",
                                        "focus": "performance",
                                    })
                                    break

        except SyntaxError:
            pass

    # Generic: duplicate code detection (simple line-based)
    if focus in ("patterns", "all") and len(lines) > 20:
        line_counts = {}
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if len(stripped) > 20 and not stripped.startswith("#"):
                if stripped in line_counts:
                    line_counts[stripped].append(i)
                else:
                    line_counts[stripped] = [i]
        for line_content, occurrences in line_counts.items():
            if len(occurrences) >= 3:
                suggestions.append({
                    "type": "duplicate_code",
                    "severity": "warning",
                    "line": occurrences[0],
                    "message": f"Line repeated {len(occurrences)}x (lines {occurrences[:5]}) — extract to function/constant",
                    "focus": "patterns",
                })

    return {
        "path": abs_path,
        "language": lang,
        "suggestions_count": len(suggestions),
        "suggestions": sorted(suggestions, key=lambda x: x.get("line", 0))[:40],
        "applied": False,
    }


# =============================================================================
# git — Unified Git Operations
# =============================================================================

async def handle_git(params: Dict[str, Any]) -> Dict[str, Any]:
    mode = params.get("mode", "status")
    message = params.get("message", "")
    branch = params.get("branch", "")
    path = params.get("path", str(PROJECT_ROOT))
    args = params.get("args", "")

    abs_path = path if path.startswith("/") else str(PROJECT_ROOT / path)

    cmd_map = {
        "status": "git status --short --branch",
        "diff": f"git diff {args}",
        "commit": f'git add -A && git commit -m "{message}"' if message else "git status",
        "branch": f"git branch {branch} && git checkout {branch}" if branch else "git branch -a",
        "log": f"git log --oneline -20 {args}",
        "push": f"git push {args}",
        "pull": f"git pull {args}",
        "stash": f"git stash {args}",
        "add": f"git add {args or '.'}",
    }

    cmd = cmd_map.get(mode, "git status")

    if mode == "commit" and not message:
        return {"error": "message is required for commit mode"}

    r = _run(cmd, cwd=abs_path, timeout=30)
    return {
        "mode": mode,
        "path": abs_path,
        "output": r["stdout"] or r["stderr"],
        "exit_code": r["exit_code"],
        "success": r["exit_code"] == 0,
    }


# =============================================================================
# HANDLER REGISTRY
# =============================================================================

DEV_TOOL_HANDLERS = {
    "dev_analyze": handle_dev_analyze,
    "dev_lint": handle_dev_lint,
    "dev_debug": handle_dev_debug,
    "dev_summarize": handle_dev_summarize,
    "dev_links": handle_dev_links,
    "dev_refactor": handle_dev_refactor,
    "git": handle_git,
    # Git aliases
    "git_status": lambda p: handle_git({**p, "mode": "status"}),
    "git_diff": lambda p: handle_git({**p, "mode": "diff"}),
    "git_commit": lambda p: handle_git({**p, "mode": "commit"}),
    "git_branch": lambda p: handle_git({**p, "mode": "branch"}),
}

DEV_TOOL_NAMES = list(DEV_TOOL_HANDLERS.keys())
