# MCP Tool Consolidation - Migration Guide
# ==========================================
# Version: 4.0.0
# Date: 2025-12-26
# Author: Claude (via AILinux MCP)

## Summary

Reduced from **134 tools** to **52 tools** (~61% reduction).

## Changes by Category

### Removed Duplicates
| Old Tools | Merged Into |
|-----------|-------------|
| `list_models`, `tristar_models` | `models` |
| `web_search`, `crawl_url` | `search`, `crawl` |
| `cli-agents_list`, `queue_agents` | `agents` |
| `cli-agents_call` | `agent_call` |
| `cli-agents_broadcast`, `queue_broadcast` | `agent_broadcast` |
| `codebase_file` | `code_read` |
| `codebase_search`, `ram_search` | `code_search` |
| `codebase_edit` | `code_edit` |
| `codebase_structure`, `code_scout` | `code_tree` |
| `ram_patch_apply` | `code_patch` |
| `ollama_generate`, `ollama_chat` | `ollama_run` |
| `ollama_health`, `ollama_ps` | `ollama_status` |
| `triforce_logs_*`, `tristar_logs` | `logs`, `logs_errors`, `logs_stats` |
| `tristar_settings*` | `config`, `config_set` |
| `tristar_prompts_*` | `prompts`, `prompt_set` |

### Removed (Low Usage)
- `ollama_copy` - rarely used
- `ollama_push` - rarely used  
- `ollama_create` - rarely used
- `decode_shortcode` - internal only
- `execute_shortcode` - internal only
- `process_agent_output` - internal only
- `loadbalancer_stats` - internal only
- `mcp_brain_status` - internal only
- `rate_limit_stats` - internal only
- `execution_log` - internal only
- `wakeup_agent` - use `agent_start`
- `mesh_filter_check` - internal only
- `mesh_filter_audit` - internal only
- `mesh_queue_command` - use `mesh_task`
- All TRISTAR_CONVERSATIONS tools - use memory instead
- `gemini_init_all`, `gemini_init_model` - use `init`
- `gemini_get_models` - use `models`
- `gemini_quick` - use `gemini_research`
- `gemini_update` - use `memory_store`
- `gemini_function_call` - internal

### Renamed for Clarity
| Old Name | New Name | Reason |
|----------|----------|--------|
| `ask_specialist` | `specialist` | Shorter |
| `tristar_memory_store` | `memory_store` | No prefix |
| `tristar_memory_search` | `memory_search` | No prefix |
| `tristar_shell_exec` | `shell` | Shorter |
| `tristar_status` | `status` | No prefix |
| `restart_backend`, `restart_agent` | `restart` | Unified |
| `bootstrap_agents` | `bootstrap` | Shorter |
| `evolve_analyze` | `evolve` | Shorter |
| `gemini_code_exec` | `gemini_exec` | Shorter |
| `mesh_get_status` | `mesh_status` | Clearer |
| `mesh_submit_task` | `mesh_task` | Shorter |
| `mesh_list_agents` | `mesh_agents` | Shorter |

## New Tool Categories (15)

1. **core** (3): chat, models, specialist
2. **search** (2): search, crawl
3. **memory** (3): memory_store, memory_search, memory_clear
4. **agents** (5): agents, agent_call, agent_broadcast, agent_start, agent_stop
5. **code** (5): code_read, code_search, code_edit, code_tree, code_patch
6. **ollama** (6): ollama_list, ollama_pull, ollama_delete, ollama_run, ollama_embed, ollama_status
7. **logs** (3): logs, logs_errors, logs_stats
8. **config** (4): config, config_set, prompts, prompt_set
9. **system** (5): status, shell, restart, health, debug
10. **vault** (3): vault_keys, vault_add, vault_status
11. **remote** (3): remote_hosts, remote_task, remote_status
12. **evolve** (2): evolve, evolve_history
13. **init** (2): init, bootstrap
14. **gemini** (3): gemini_research, gemini_coordinate, gemini_exec
15. **mesh** (3): mesh_status, mesh_task, mesh_agents

## Backwards Compatibility

The `TOOL_ALIASES` dict in `tool_registry_v4.py` maps all old names to new names.
Existing code calling old tool names will continue to work.

## Migration Steps

1. ✅ Created `tool_registry_v4.py` with consolidated tools
2. ✅ Created `handlers_v4.py` with handler mappings
3. ✅ Backup of `tool_registry_v3.py`
4. ⏳ Update `mcp.py` to use v4 registry
5. ⏳ Test all tool calls
6. ⏳ Remove deprecated adaptive_code_v4.py (redundant with v3)
7. ⏳ Update documentation

## Files Changed

- `app/mcp/tool_registry_v4.py` - NEW (consolidated tools)
- `app/mcp/handlers_v4.py` - NEW (handler mappings)
- `app/mcp/tool_registry_v3.py` - BACKUP CREATED
- `app/mcp/adaptive_code_v4.py` - TO BE REMOVED (duplicate)

## Rollback

If issues occur, restore from backup:
```bash
cp .backups/app_mcp_tool_registry_v3.py_20251226_080338.bak app/mcp/tool_registry_v3.py
```

And revert imports in `mcp.py` to use v3.
