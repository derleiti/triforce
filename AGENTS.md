# Repository Guidelines

## Project Structure & Module Organization
- `app/`: FastAPI backend with routes (`routes/`), services (`services/`), MCP handlers (`mcp/`), and shared utilities (`config.py`, `main.py`).
- `tests/`: Pytest suite covering MCP, integrations, and services.
- `bin/`: CLI tools (`tristar` orchestration CLI, startup scripts) and TUI helpers.
- `docs/`, `README.md`: Protocol docs and quick start; `systemd/` holds service unit templates; `node_modules/` and `nova-ai-frontend*/` are frontend assets (mostly untouched for backend work).
- Config lives in `.env` (copy from `.env.example`) with provider keys and ports.

## Build, Test, and Development Commands
- Install deps: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Run dev server (FastAPI): `.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9100 --reload`
- Smoke MCP endpoints: `curl -X POST http://localhost:9100/mcp -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'`
- Tests: `.venv/bin/pytest` or target a file, e.g. `.venv/bin/pytest tests/test_mcp.py -v`
- CLI check: `bin/tristar status` (prefers local `http://localhost:9100/v1/mcp`)

## Coding Style & Naming Conventions
- Python 3.11+, PEP8; prefer type hints and async/await for I/O. Keep functions small and log via existing loggers (see `logging.getLogger("ailinux.*")`).
- Route handlers live in `app/routes/`; service logic belongs in `app/services/`; keep MCP tools in dedicated handler modules.
- Name MCP methods with dotted namespaces (`llm.invoke`, `admin.crawler.config.set`) and keep JSON-RPC payloads snake_case.

## Testing Guidelines
- Framework: pytest; async tests use `@pytest.mark.asyncio`. Mock external calls (LLM, HTTP, Ollama) like in `tests/test_mcp.py`.
- Add focused tests per service file; name tests `test_<behavior>` and mirror module paths under `tests/`.
- Prefer fast, offline tests; gate network/API-key cases with `@pytest.mark.skipif`.

## Commit & Pull Request Guidelines
- Commits: short imperative subject (<=72 chars), optional body for rationale; align scope to a single concern (e.g., “fix mcp llm.invoke token accounting”).
- PRs: include summary, scope (routes/services touched), testing proof (`pytest ...` output or curl snippet), and any config/env changes. Link issues/tickets and add screenshots for UI-affecting changes.

## Security & Configuration Tips
- Never commit secrets; load keys via `.env` only. Redis and provider endpoints are assumed local by default—avoid embedding public URLs.
- MCP/Tristar ports default to 9100; update scripts if you change them. Use localhost endpoints for agent calls to stay offline.
