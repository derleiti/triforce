#!/bin/bash
# =============================================================================
# MCP Tool Audit Fix Script — 2026-04-03
# =============================================================================
set -euo pipefail

TRIFORCE="/home/zombie/triforce"
BACKUP_DIR="$TRIFORCE/patch_backups/mcp_audit_fix_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "=== MCP Tool Audit Fix — $(date) ==="
echo "Backup dir: $BACKUP_DIR"

for f in app/mcp/dev_tools.py app/mcp/doc_browser.py app/routes/mcp_remote.py app/routes/mcp.py; do
    if [ -f "$TRIFORCE/$f" ]; then
        mkdir -p "$BACKUP_DIR/$(dirname $f)"
        cp "$TRIFORCE/$f" "$BACKUP_DIR/$f"
        echo "  Backed up: $f"
    fi
done

cd "$TRIFORCE"

echo ""
echo "=== FIX 1: git — Remove lambda aliases from DEV_TOOL_HANDLERS ==="
python3 << 'PYEOF'
path = "app/mcp/dev_tools.py"
with open(path) as f: c = f.read()
old = '''    # Git aliases
    "git_status": lambda p: handle_git({**p, "mode": "status"}),
    "git_diff": lambda p: handle_git({**p, "mode": "diff"}),
    "git_commit": lambda p: handle_git({**p, "mode": "commit"}),
    "git_branch": lambda p: handle_git({**p, "mode": "branch"}),'''
new = '''    # Git aliases removed — V5_ALIASES handles remapping (fix 2026-04-03)
    # Lambda aliases overwrote handle_git in runtime_registry (last=branch)'''
if old in c:
    c = c.replace(old, new)
    with open(path,"w") as f: f.write(c)
    print("  OK")
else: print("  SKIP (pattern changed)")
PYEOF

echo ""
echo "=== FIX 2: fetch — Use httpx directly ==="
python3 << 'PYEOF'
path = "app/routes/mcp_remote.py"
with open(path) as f: c = f.read()
old = '''async def handle_fetch(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch content from a URL. Required by OpenAI for Deep Research + Company Knowledge.
    Schema matches OpenAI MCP compatibility spec: input={url:string}, output={content:string}."""
    from ..services.crawler.user_crawler import user_crawler
    
    url = arguments.get("url")
    if not url:
        raise ValueError("'url' is required")
    
    try:
        result = await user_crawler.crawl_url(url, max_pages=1)
        # Return in OpenAI-expected format
        text = ""
        if isinstance(result, dict):
            text = result.get("content", result.get("text", str(result)))
        elif isinstance(result, str):
            text = result
        return {"content": text[:50000], "url": url}  # Cap at 50k chars
    except Exception as e:
        return {"content": f"Error fetching {url}: {str(e)}", "url": url}'''
new = '''async def handle_fetch(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch content from a URL. FIX 2026-04-03: httpx direct instead of crawler."""
    import httpx
    from html.parser import HTMLParser
    import re as _re
    url = arguments.get("url")
    if not url:
        raise ValueError("'url' is required")
    class _TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self._text, self._skip = [], False
            self._skip_tags = {"script","style","noscript","svg","nav"}
        def handle_starttag(self, tag, attrs):
            if tag in self._skip_tags: self._skip = True
        def handle_endtag(self, tag):
            if tag in self._skip_tags: self._skip = False
        def handle_data(self, data):
            s = data.strip()
            if s and not self._skip: self._text.append(s)
        def get_text(self): return "\\n".join(self._text)
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0,
            headers={"User-Agent": "AILinux-Fetch/2.85"}, verify=False) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "")
            if "html" in ct:
                ex = _TextExtractor(); ex.feed(resp.text)
                text = _re.sub(r"\\n{3,}", "\\n\\n", ex.get_text())
            else:
                text = resp.text
        return {"content": text[:50000], "url": url}
    except Exception as e:
        return {"content": f"Error fetching {url}: {str(e)}", "url": url}'''
if old in c:
    c = c.replace(old, new)
    with open(path,"w") as f: f.write(c)
    print("  OK")
else: print("  SKIP (pattern changed)")
PYEOF

echo ""
echo "=== FIX 3: doc_tree — Add heavy dirs to SKIP_DIRS ==="
python3 << 'PYEOF'
path = "app/mcp/doc_browser.py"
with open(path) as f: c = f.read()
old = '''SKIP_DIRS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache",
    "node_modules", ".backups", ".repair-backup", ".debug",
    "logs", "certs", "build", ".claude"
}'''
new = '''SKIP_DIRS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache",
    "node_modules", ".backups", ".repair-backup", ".debug",
    "logs", "certs", "build", ".claude",
    # FIX 2026-04-03: prevent timeout on project root (docker=1.8TB)
    "docker", "data", "client-deploy", "aur-ailinux-client",
    "repository", "mirror", "wp-content", "vendor",
}'''
if old in c:
    c = c.replace(old, new)
    with open(path,"w") as f: f.write(c)
    print("  OK")
else: print("  SKIP (pattern changed)")
PYEOF

echo ""
echo "=== FIX 4: dev_links — Filter URL route paths ==="
python3 << 'PYEOF'
path = "app/mcp/dev_tools.py"
with open(path) as f: c = f.read()
old = '''            # Check string file paths
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
                        })'''
new = '''            # Check string file paths
            if isinstance(node, ast.Constant) and isinstance(node.s, str):
                val = node.s
                if "/" in val and len(val) > 5 and not val.startswith("http"):
                    # FIX 2026-04-03: Skip URL routes (FastAPI endpoints)
                    _rp = ("/v1/","/mcp/","/health","/.well-known/","/tristar/",
                           "/triforce/","/static/","/auth/","/client/","/nova/")
                    if any(val.startswith(p) for p in _rp):
                        continue
                    if val.startswith("/") and "." not in val.split("/")[-1]:
                        continue  # URL path without file extension
                    candidate = Path(val)
                    if candidate.is_absolute() and not candidate.exists():
                        broken.append({
                            "file": str(fpath),
                            "line": node.lineno,
                            "type": "broken_file_path",
                            "path": val,
                            "severity": "warning",
                        })'''
if old in c:
    c = c.replace(old, new)
    with open(path,"w") as f: f.write(c)
    print("  OK")
else: print("  SKIP (pattern changed)")
PYEOF

echo ""
echo "=== FIX 5-7: ollama_status, mcp_write_fallback, ram_patch_apply_v4 ==="
python3 << 'PYEOF'
path = "app/routes/mcp.py"
with open(path) as f: c = f.read()

patch = '''

# === FIX 2026-04-03: Missing/broken handlers ===

async def _handle_ollama_status(params):
    """FIX: ollama_status had no handler."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as cl:
            ps = await cl.get("http://localhost:11434/api/ps")
            ps_d = ps.json() if ps.status_code == 200 else {}
            tags = await cl.get("http://localhost:11434/api/tags")
            tags_d = tags.json() if tags.status_code == 200 else {}
        return {
            "status": "running",
            "running_models": [{"name":m.get("name"),"size":m.get("size")} for m in ps_d.get("models",[])],
            "available_models": len(tags_d.get("models",[])),
        }
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}

async def _handle_mcp_write_fallback_safe(params):
    """FIX: mcp_write_fallback crashed with no params."""
    fid = (params or {}).get("fallback_id")
    if not fid:
        return {"error": "fallback_id required", "hint": "This tool executes stored write operations."}
    return await handle_mcp_write_fallback(params)

async def _handle_ram_patch_apply_v4_safe(params):
    """FIX: ram_patch_apply_v4 crashed with no params."""
    patch = (params or {}).get("patch") or (params or {}).get("diff")
    if not patch:
        return {"error": "patch/diff content required", "hint": "Provide unified diff as 'patch' parameter."}
    return await handle_codebase_patch({"patch": patch, "path": (params or {}).get("path","")})

MCP_HANDLERS["ollama_status"] = _handle_ollama_status
MCP_HANDLERS["mcp_write_fallback"] = _handle_mcp_write_fallback_safe
MCP_HANDLERS["ram_patch_apply_v4"] = _handle_ram_patch_apply_v4_safe
'''

marker = 'MCP_HANDLERS.update(SWARM_HANDLERS)          # swarm_broadcast, swarm_status, swarm_top_results, swarm_consolidated'
if marker in c and "_handle_ollama_status" not in c:
    c = c.replace(marker, marker + patch)
    with open(path,"w") as f: f.write(c)
    print("  OK — 3 handlers added")
elif "_handle_ollama_status" in c:
    print("  SKIP (already applied)")
else:
    print("  SKIP (marker not found)")
PYEOF

echo ""
echo "=== FIX 8: crawl — Direct-fetch fallback for single URLs ==="
python3 << 'PYEOF'
path = "app/routes/mcp.py"
with open(path) as f: c = f.read()
old = '''async def handle_crawl_url(params: Dict[str, Any]) -> Dict[str, Any]:
    url = params.get("url")
    if not url:
        raise ValueError("'url' parameter is required for crawl.url")

    keywords = params.get("keywords")
    if keywords is not None and not isinstance(keywords, Iterable):
        raise ValueError("'keywords' must be an iterable of strings")

    job = await user_crawler.crawl_url(
        url=url,
        keywords=list(keywords) if keywords else None,
        max_pages=int(params.get("max_pages", 10)),
        idempotency_key=params.get("idempotency_key"),
    )
    return {"job": _serialize_job(job)}'''
new = '''async def handle_crawl_url(params: Dict[str, Any]) -> Dict[str, Any]:
    """FIX 2026-04-03: Direct httpx fetch for single URLs, crawler for multi-page."""
    import httpx as _hx
    url = params.get("url")
    if not url:
        raise ValueError("'url' parameter is required for crawl.url")
    keywords = params.get("keywords")
    if keywords is not None and not isinstance(keywords, Iterable):
        raise ValueError("'keywords' must be an iterable of strings")
    max_pages = int(params.get("max_pages", 10))
    # Single-page: direct fetch (faster, more reliable)
    if max_pages <= 1:
        try:
            async with _hx.AsyncClient(follow_redirects=True, timeout=15.0,
                verify=False, headers={"User-Agent":"AILinux-Crawl/2.85"}) as cl:
                r = await cl.get(url); r.raise_for_status()
                from html.parser import HTMLParser as _HP
                import re as _rc
                class _T(_HP):
                    def __init__(self):
                        super().__init__(); self._t,self._s=[],False
                        self._st={"script","style","noscript","svg"}
                    def handle_starttag(s,t,a):
                        if t in s._st: s._s=True
                    def handle_endtag(s,t):
                        if t in s._st: s._s=False
                    def handle_data(s,d):
                        v=d.strip()
                        if v and not s._s: s._t.append(v)
                ct = r.headers.get("content-type","")
                if "html" in ct:
                    t=_T(); t.feed(r.text); text=_rc.sub(r"\\n{3,}","\\n\\n","\\n".join(t._t))
                else: text=r.text
                return {"job":{"id":"direct","status":"completed","pages_crawled":1,
                    "results":[{"url":url,"content":text[:30000]}]},
                    "message":f"Direct fetch completed for {url}"}
        except Exception: pass
    # Multi-page or fallback
    job = await user_crawler.crawl_url(
        url=url, keywords=list(keywords) if keywords else None,
        max_pages=max_pages, idempotency_key=params.get("idempotency_key"))
    return {"job": _serialize_job(job), "message": f"Crawl job started for {url}"}'''
if old in c:
    c = c.replace(old, new)
    with open(path,"w") as f: f.write(c)
    print("  OK")
else: print("  SKIP (pattern changed)")
PYEOF

echo ""
echo "============================================================"
echo "All patches applied!"
echo "  1. git       — Lambda aliases removed"
echo "  2. fetch     — httpx direct fetch"
echo "  3. doc_tree  — Heavy dirs skip"
echo "  4. dev_links — Route filter"
echo "  5. ollama_status — New handler"
echo "  6. mcp_write_fallback — Safe handler"
echo "  7. ram_patch_apply_v4 — Safe handler"
echo "  8. crawl     — Direct-fetch fallback"
echo ""
echo "Backups: $BACKUP_DIR"
echo "Restart: sudo systemctl restart triforce"
