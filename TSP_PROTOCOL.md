# Token-Saver Protocol (TSP) v2

This protocol is designed to minimize token usage during communication with TriForce coding agents (`claude-mcp`, `codex-mcp`). It is embedded in the agent system prompts served by `api.ailinux.me`.

## Syntax
The protocol uses short directives starting with `§` (Paragraph sign) for actions, and `@` for references.

### Directives (Actions)

| Shortcut | Arguments | Description |
| :--- | :--- | :--- |
| **`§C`** | `[Lang] [Desc]` | **Code Generation**. Generate code in the specified language. |
| **`§R`** | `[Target]` | **Review**. Perform a code review on the target. |
| **`§F`** | `[Target]` | **Fix**. Analyze errors/bugs in the target and provide a fix. |
| **`§T`** | `[Target]` | **Test**. Generate unit tests for the target. |
| **`§E`** | `[Topic]` | **Explain**. Provide a concise explanation. |
| **`§S`** | `[File]` | **Save**. Provide instructions to save content. |
| **`§X`** | `[Cmd]` | **Execute**. Run a shell command. |

### References (Context/Targets)

| Marker | Description | Example |
| :--- | :--- | :--- |
| **`@File`** | Reference a file path. Implies reading/using its content. | `@app/main.py` |
| **`@Dir`** | Reference a directory. | `@app/routes/` |
| **`@Agent`** | Address or delegate to a specific agent. | `@codex`, `@claude` |
| **`@Url`** | Reference a web URL. | `@https://docs.python.org` |
| **`@Mem`** | Reference a memory ID or tag. | `@mem_123`, `@tag:auth` |

### Context Markers

| Marker | Description |
| :--- | :--- |
| **`>`** | **Input Context**. The text following this marker is raw context. |
| **`<`** | **Output Expectation**. The text following this marker describes the desired format. |

## Examples

**Generate code with file context:**
```text
§C Python @app/routes/items.py
> Create CRUD endpoints similar to @app/routes/users.py
```

**Review a file:**
```text
§R @app/main.py
< focus on security
```

**Delegate to Codex:**
```text
@codex §F @app/utils.py
> IndexError in list processing
```

## Implementation
This protocol is registered in the system prompts via the `tristar_agent_configure` tool.