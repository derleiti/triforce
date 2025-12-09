# TriForce MCP System - Feature-Referenz für Claude Coding Agent
## Version 2.80.0 | 131 MCP Tools | 18 Kategorien

---

## 🛠️ TOOL-KATEGORIEN (131 Tools)

### 1. CORE (4 Tools)
```
chat, list_models, ask_specialist, crawl_url
```

### 2. SEARCH (8 Tools)
```
web_search, smart_search, quick_smart_search, multi_search,
google_deep_search, search_health, ailinux_search, grokipedia_search
```

### 3. REALTIME (6 Tools)
```
weather, crypto_prices, stock_indices, market_overview,
current_time, list_timezones
```

### 4. CODEBASE (20 Tools)
```
codebase_structure, codebase_file, codebase_search, codebase_routes,
codebase_services, codebase_edit, codebase_create, codebase_backup,
code_scout, code_probe, ram_search, ram_context_export, ram_patch_apply,
code_scout_v4, code_probe_v4, ram_search_v4, delta_sync_v4,
cache_stats_v4, cache_invalidate_v4, checkpoint_create_v4
```

### 5. AGENTS (9 Tools)
```
cli-agents_list, cli-agents_get, cli-agents_start, cli-agents_stop,
cli-agents_restart, cli-agents_call, cli-agents_broadcast, cli-agents_output,
cli-agents_stats
```

### 6. MEMORY (7 Tools)
```
tristar_memory_store, tristar_memory_search, memory_index_add,
memory_index_search, memory_index_get, memory_index_compact, memory_index_stats
```

### 7. OLLAMA (12 Tools)
```
ollama_list, ollama_show, ollama_pull, ollama_push, ollama_copy,
ollama_delete, ollama_create, ollama_ps, ollama_generate, ollama_chat,
ollama_embed, ollama_health
```

### 8. MESH (7 Tools)
```
mesh_submit_task, mesh_queue_command, mesh_get_status, mesh_list_agents,
mesh_get_task, mesh_filter_check, mesh_filter_audit
```

### 9. QUEUE (6 Tools)
```
queue_enqueue, queue_research, queue_status, queue_get,
queue_agents, queue_broadcast
```

### 10. GEMINI (9 Tools)
```
gemini_research, gemini_coordinate, gemini_quick, gemini_update,
gemini_function_call, gemini_code_exec, gemini_init_all, gemini_init_model,
gemini_get_models
```

### 11. TRISTAR (21 Tools)
```
tristar_models, tristar_init, tristar_logs, tristar_logs_agent,
tristar_logs_clear, tristar_prompts_list, tristar_prompts_get,
tristar_prompts_set, tristar_prompts_delete, tristar_settings,
tristar_settings_get, tristar_settings_set, tristar_conversations,
tristar_conversation_get, tristar_conversation_save, tristar_conversation_delete,
tristar_agents, tristar_agent_config, tristar_agent_configure, tristar_status,
tristar_shell_exec
```

### 12. TRIFORCE LOGS (5 Tools)
```
triforce_logs_recent, triforce_logs_errors, triforce_logs_api,
triforce_logs_trace, triforce_logs_stats
```

### 13. INIT (7 Tools)
```
init, compact_init, tool_lookup, decode_shortcode, execute_shortcode,
loadbalancer_stats, mcp_brain_status
```

### 14. BOOTSTRAP (6 Tools)
```
bootstrap_agents, wakeup_agent, bootstrap_status, process_agent_output,
rate_limit_stats, execution_log
```

### 15. EVOLVE (3 Tools)
```
evolve_analyze, evolve_history, evolve_broadcast
```

### 16. LLM_COMPAT (2 Tools)
```
llm_compat_convert, llm_compat_parse
```

### 17. HOTRELOAD (6 Tools)
```
hot_reload_module, hot_reload_services, hot_reload_all,
list_reloadable_modules, reinit_service, reload_history
```

### 18. HUGGINGFACE (7 Tools)
```
hf_generate, hf_chat, hf_embed, hf_image, hf_summarize,
hf_translate, hf_models
```

### 19. DEBUG (6 Tools)
```
debug_mcp_request, check_compatibility, restart_backend, restart_agent,
debug_toolchain, execute_mcp_tool
```

---

## 🎯 SHORTCODE PROTOKOLL v2.0

### Agent-Aliase
| Kurz | Lang | Agent ID |
|------|------|----------|
| @c | @claude | claude-mcp |
| @g | @gemini | gemini-mcp (Lead) |
| @x | @codex | codex-mcp |
| @m | @mistral | mistral-mcp |
| @d | @deepseek | deepseek-mcp |
| @n | @nova | nova-mcp |
| @* | @all | broadcast |

### Actions
```
!g=generate, !c=code, !r=review, !s=search, !f=fix, 
!a=analyze, !m=mem, !x=exec, !t=test, !e=explain, !sum=summarize
```

### Flow-Operatoren
```
>=send, >>=chain, <=return, <<=final, |=pipe
```

### Beispiele
```
@g>!s"linux kernel"=[r]>>@c>!sum@[r]   # Gemini sucht, Claude fasst zusammen
@c>!code"REST API"#backend!!            # Claude schreibt Code, high priority
@*>!query"status"                       # Broadcast an alle Agents
```

---

## 🔌 API ENDPOINTS

### REST API
- `POST /v1/chat/completions` - Chat
- `GET /v1/models` - Modelle auflisten
- `POST /v1/search` - Suche

### MCP Protocol
- `POST /mcp` - MCP Requests
- `GET /v1/mcp/init` - Init mit Dokumentation
- `GET /v1/mcp/status` - Status

### TriForce
- `POST /triforce/mesh/call` - Single LLM
- `POST /triforce/mesh/broadcast` - Multi LLM
- `POST /triforce/mesh/consensus` - Konsens

---

## 📁 PROJEKTSTRUKTUR

```
/home/zombie/ailinux-ai-server-backend/
├── app/
│   ├── routes/          # FastAPI Routes
│   ├── services/        # Business Logic
│   ├── mcp/             # MCP Tools & Registry
│   └── utils/           # Utilities
├── mailserver/          # Docker Mailserver (config excluded)
├── ailinux-repo/        # APT Repository (repo excluded)
├── wordpress-plugins/   # Nova AI Frontend
└── .gitignore           # Mit allen Excludes
```

---

## 🚀 QUICK START für Claude Coding Agent

1. **Init holen:** `POST /v1/mcp/init`
2. **Tool lookup:** `tool_lookup(tool_name="chat")`
3. **Code ändern:** `codebase_edit(path, mode="replace", old_text, new_text)`
4. **Hot Reload:** `hot_reload_services()` (kein Backend-Neustart nötig!)
5. **Verifizieren:** `check_compatibility()`

---

*Generated: 2025-12-09 | TriForce v2.80.0*
