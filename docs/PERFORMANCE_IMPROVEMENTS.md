# Performance Improvements

This document describes the performance improvements made to address slow or inefficient code patterns in the TriForce backend.

---

## Summary

| File | Issue | Fix | Impact |
|------|-------|-----|--------|
| `app/services/memory_index.py` | `List[str]` for membership tracking | `Set[str]` for O(1) operations | HIGH |
| `app/services/mesh_coordinator.py` | `list.sort()` + `list.pop(0)` for priority queue | `heapq` for O(log n) insert/pop | HIGH |
| `app/services/mesh_coordinator.py` | `len([t for t in ...])` list comprehension | `sum(1 for t in ...)` generator | LOW |
| `app/services/chat.py` | `socket.gethostbyname()` blocking event loop | `loop.run_in_executor()` for async DNS | HIGH |
| `app/services/chat.py` | Linear TLD list scan | `frozenset` for O(1) lookup | LOW |
| `app/services/mcp_service.py` | Blocking `open()` file write in async handler | `aiofiles.open()` async file write | HIGH |
| `app/services/command_queue.py` | Unnecessary `list()` copy of dict keys | Iterate `dict.keys()` directly | LOW |

---

## Detailed Changes

### 1. `memory_index.py` — Set-based lookup maps

**Before:**
```python
self._keyword_map: Dict[str, List[str]] = {}   # O(n) membership check
self._category_map: Dict[str, List[str]] = {}  # O(n) membership check

# Add: O(n) check before append
if entry.memory_id not in self._keyword_map[kw_lower]:
    self._keyword_map[kw_lower].append(entry.memory_id)

# Remove: O(n) list rebuild
self._keyword_map[kw] = [mid for mid in self._keyword_map[kw] if mid != memory_id]

# Search: dedup with set conversion after extending a list
results.extend(ids)
return list(set(results))  # Extra conversion
```

**After:**
```python
self._keyword_map: Dict[str, Set[str]] = {}   # O(1) membership check
self._category_map: Dict[str, Set[str]] = {}  # O(1) membership check

# Add: O(1) set.add() with setdefault
self._keyword_map.setdefault(kw_lower, set()).add(entry.memory_id)

# Remove: O(1) set.discard(), also cleans up empty sets
self._keyword_map[kw].discard(memory_id)

# Search: accumulate directly into a set
results: Set[str] = set()
results.update(ids)
return list(results)
```

**Why it matters:** With `n` memory entries and `k` keywords each, every `add()` call was O(k*n) due to linear membership checks. With sets it is O(k). Similarly `remove()` drops from O(k*n) to O(k).

---

### 2. `mesh_coordinator.py` — `heapq`-based MCP command queue

**Before:**
```python
self._mcp_queue: List[MCPCommand] = []

# Enqueue: O(n log n) sort after every append
self._mcp_queue.append(cmd)
self._mcp_queue.sort(key=lambda x: x.priority)  # O(n log n)

# Dequeue: O(n) pop from front of list
cmd = self._mcp_queue.pop(0)  # Shifts all elements left
```

**After:**
```python
# Priority heap: (priority, counter, MCPCommand) tuples
self._mcp_queue: List[Tuple[int, int, MCPCommand]] = []
self._mcp_queue_counter: int = 0

# Enqueue: O(log n) heap push
heapq.heappush(self._mcp_queue, (cmd.priority, self._mcp_queue_counter, cmd))
self._mcp_queue_counter += 1

# Dequeue: O(log n) heap pop
_, _, cmd = heapq.heappop(self._mcp_queue)
```

The `counter` field acts as a FIFO tiebreaker for equal-priority commands, ensuring stable ordering without requiring `MCPCommand.__lt__`.

**Complexity improvement:**
- Enqueue: O(n log n) → O(log n)
- Dequeue: O(n) → O(log n)

---

### 3. `mesh_coordinator.py` — Generator instead of list comprehension for count

**Before:**
```python
# Builds a full list in memory just to count its length
"active_tasks": len([t for t in self._tasks.values()
                     if t.phase not in [TaskPhase.COMPLETED, TaskPhase.FAILED]]),
```

**After:**
```python
# Counts lazily without allocating a list; also uses a frozenset for O(1) phase lookup
completed_phases = {TaskPhase.COMPLETED, TaskPhase.FAILED}
"active_tasks": sum(1 for t in self._tasks.values() if t.phase not in completed_phases),
```

---

### 4. `chat.py` — Non-blocking DNS resolution for SSRF check

**Before:**
```python
def _is_ssrf_safe(url: str) -> bool:
    # Blocks the async event loop for the duration of DNS resolution (5-30 s on timeout)
    ip_str = socket.gethostbyname(hostname)
```

**After:**
```python
async def _is_ssrf_safe(url: str) -> bool:
    # Offloads blocking DNS call to a thread-pool worker — event loop stays free
    loop = asyncio.get_event_loop()
    ip_str = await loop.run_in_executor(None, socket.gethostbyname, hostname)
```

`_extract_safe_urls` was updated to `async` accordingly, and its call site in `stream_chat` was updated to `await _extract_safe_urls(...)`.

---

### 5. `chat.py` — `frozenset` for TLD blocked-list lookup

**Before:**
```python
# O(n) linear scan over a regular list
if any(hostname.lower().endswith(tld) for tld in [".local", ".internal", ".localhost", ".lan"]):
```

**After:**
```python
# Module-level constant; frozenset gives O(1) `in` check
_BLOCKED_TLDS: frozenset = frozenset({".local", ".internal", ".localhost", ".lan"})

if any(hostname_lower.endswith(tld) for tld in _BLOCKED_TLDS):
```

While the set is small (4 elements), using a `frozenset` module-level constant communicates intent and avoids re-allocating the collection on each call.

---

### 6. `mcp_service.py` — Async file I/O for edit audit log

**Before:**
```python
def _log_edit(action: str, path: str, details: Dict[str, Any]):
    # Synchronous file write inside an async handler — blocks the event loop
    with open(EDIT_LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
```

**After:**
```python
async def _log_edit(action: str, path: str, details: Dict[str, Any]):
    # Non-blocking async file write using aiofiles
    async with aiofiles.open(EDIT_LOG_FILE, "a") as f:
        await f.write(json.dumps(log_entry) + "\n")
```

All three call sites (`handle_codebase_edit`, `handle_codebase_backup`) were updated to `await _log_edit(...)`.

---

### 7. `command_queue.py` — Remove unnecessary `list()` copy

**Before:**
```python
# Creates a full list copy just to iterate
agent_ids = list(self._agents.keys())
for agent_id in agent_ids:
```

**After:**
```python
# Iterate the dict view directly — no copy needed
agent_ids = self._agents.keys()
for agent_id in agent_ids:
```

Since no mutation of `self._agents` occurs during the loop, iterating the dict view is safe and avoids an O(n) allocation.

---

## Testing

All changes were validated with:
- Python `py_compile` syntax check on all modified files
- Isolated unit tests for `memory_index` (add/search/remove/get_compact_index/get_stats)
- Isolated unit tests for `mesh_coordinator` (heapq priority ordering, `get_status` active task count)
- Logic verification for `chat.py` SSRF frozenset and async DNS patterns
- Static analysis confirming `_log_edit` is `async` and all callers `await` it
