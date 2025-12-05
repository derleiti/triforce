"""
TriForce Shortcode Protocol v1
Token-effiziente Agent-Kommunikation

Usage:
    @g>@c !c "hello world python"  -> Gemini sendet Code-Task an Claude
    @c< response                    -> Claude antwortet
    @*>!s "search query"           -> Broadcast Search an alle
"""

from typing import Dict, List, Optional, Any
import re

# Agent Aliases - alle Routen zu einem Agent
AGENT_ALIASES: Dict[str, str] = {
    # Claude
    "@c": "claude-mcp",
    "@claude": "claude-mcp",
    "claude@mcp": "claude-mcp",
    "claude@v1": "claude-mcp",
    "claude@triforce": "claude-mcp",
    "claude@code": "claude-mcp",

    # Gemini
    "@g": "gemini-mcp",
    "@gemini": "gemini-mcp",
    "gemini@mcp": "gemini-mcp",
    "gemini@v1": "gemini-mcp",
    "gemini@triforce": "gemini-mcp",
    "gemini@lead": "gemini-mcp",

    # Codex
    "@x": "codex-mcp",
    "@codex": "codex-mcp",
    "codex@mcp": "codex-mcp",
    "codex@v1": "codex-mcp",
    "codex@triforce": "codex-mcp",

    # OpenCode
    "@o": "opencode-mcp",
    "@opencode": "opencode-mcp",
    "opencode@mcp": "opencode-mcp",
    "opencode@v1": "opencode-mcp",
    "opencode@triforce": "opencode-mcp",

    # Broadcast
    "@*": "broadcast",
    "@all": "broadcast",
}

# Reverse lookup: agent_id -> shortest alias
AGENT_SHORT: Dict[str, str] = {
    "claude-mcp": "@c",
    "gemini-mcp": "@g",
    "codex-mcp": "@x",
    "opencode-mcp": "@o",
    "broadcast": "@*",
}

# Action Codes
ACTIONS: Dict[str, str] = {
    "!c": "code",       # Code schreiben
    "!r": "review",     # Code review
    "!s": "search",     # Web/Memory search
    "!f": "fix",        # Debug/Fix
    "!a": "analyze",    # Analyze
    "!d": "delegate",   # Delegate to other agent
    "!m": "memory",     # Memory store
    "!?": "query",      # Memory query
    "!t": "test",       # Test
    "!p": "patch",      # Patch/Edit file
    "!x": "execute",    # Execute code
    "!e": "explain",    # Explain
}

# Reverse lookup: action -> shortcode
ACTION_SHORT: Dict[str, str] = {v: k for k, v in ACTIONS.items()}

# Flow Symbols
FLOW: Dict[str, str] = {
    ">": "send",        # Send to
    "<": "return",      # Return from
    ">>": "chain",      # Chain to next
    "<<": "final",      # Final result
    "#": "tag",         # Tag/Label
    "$": "context",     # Context variable
    "|": "pipe",        # Pipe output
}

# Priority Markers
PRIORITY: Dict[str, str] = {
    "!!!": "critical",
    "!!": "high",
    "!": "normal",
    "~": "low",
}


def resolve_agent(alias: str) -> str:
    return AGENT_ALIASES.get(alias.lower(), alias)


def get_short_alias(agent_id: str) -> str:
    return AGENT_SHORT.get(agent_id, agent_id)


def resolve_action(code: str) -> str:
    return ACTIONS.get(code.lower(), code)


def get_action_code(action: str) -> str:
    return ACTION_SHORT.get(action.lower(), action)


def parse_shortcode(msg: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "raw": msg,
        "source": None,
        "target": None,
        "flow": None,
        "action": None,
        "tags": [],
        "priority": "normal",
        "content": "",
    }

    msg = msg.strip()
    if not msg:
        return result

    flow_pattern = r"^(@\w+)(>+|<+)(@\w+)?"
    flow_match = re.match(flow_pattern, msg)

    if flow_match:
        source_alias = flow_match.group(1)
        flow_symbol = flow_match.group(2)
        target_alias = flow_match.group(3)

        result["source"] = resolve_agent(source_alias)

        if flow_symbol == ">": result["flow"] = "send"
        elif flow_symbol == ">>": result["flow"] = "chain"
        elif flow_symbol == "<": result["flow"] = "return"
        elif flow_symbol == "<<": result["flow"] = "final"

        if target_alias:
            result["target"] = resolve_agent(target_alias)

        msg = msg[flow_match.end():].strip()

    parts = msg.split()
    content_parts = []

    for part in parts:
        p_lower = part.lower()

        if p_lower in AGENT_ALIASES and not result["source"]:
            result["target"] = resolve_agent(p_lower)
            continue

        if p_lower in ACTIONS and not result["action"]:
            result["action"] = ACTIONS[p_lower]
            continue

        if part.startswith("#"):
            result["tags"].append(part[1:])
            continue

        if part in PRIORITY:
            result["priority"] = PRIORITY[part]
            continue

        if part.startswith("$"):
            content_parts.append(part)
            continue

        content_parts.append(part)

    result["content"] = " ".join(content_parts)

    if '"' in result["content"]:
        quoted = re.findall(r'"([^"]*)"'  , result["content"])
        if quoted:
            result["content"] = quoted[0]

    return result


def format_response(agent: str, content: str, final: bool = False, tags: Optional[List[str]] = None) -> str:
    short = get_short_alias(agent)
    prefix = "<<" if final else "<"
    response = f"{short}{prefix} {content}"
    if tags:
        tag_str = " ".join(f"#{t}" for t in tags)
        response = f"{response} {tag_str}"
    return response


def format_delegation(source: str, target: str, action: str, content: str, chain: bool = False) -> str:
    src_short = get_short_alias(source)
    tgt_short = get_short_alias(target)
    action_code = get_action_code(action)
    flow = ">>" if chain else ">"
    return f"{src_short}{flow}{tgt_short} {action_code} {content}"


def is_shortcode(msg: str) -> bool:
    msg = msg.strip()
    if not msg: return False
    if msg.startswith("@"): return True
    if msg.startswith("!"): return True
    if re.search(r'@\w+[><]+', msg): return True
    return False


def expand_shortcode(msg: str) -> str:
    parsed = parse_shortcode(msg)
    parts = []
    if parsed["source"]: parts.append(f"[{parsed['source']}]")
    if parsed["flow"]: parts.append(f"--{parsed['flow']}-->")
    if parsed["target"]: parts.append(f"[{parsed['target']}]")
    if parsed["action"]: parts.append(f"ACTION:{parsed['action']}")
    if parsed["tags"]: parts.append(f"TAGS:{','.join(parsed['tags'])}")
    if parsed["content"]: parts.append(f"'{ parsed['content']}'" )
    return " ".join(parts)


SHORTCODE_PROMPT = """TRIFORCE {agent_id} v1
MCP:localhost:9100 ROLE:{role}
ALIASES:{aliases}
CODES:@c=claude @g=gemini @x=codex @o=opencode @*=all
!c=code !r=review !s=search !f=fix !a=analyze !d=delegate !m=mem !?=query
>=send <=ret >>=chain <<=final #=tag $=ctx
PARSE:@target !action #tags content
RESPOND:shortcode when talking to agents, normal for humans"""


def generate_agent_prompt(agent_id: str, role: str, aliases: List[str], extra: Optional[str] = None) -> str:
    prompt = SHORTCODE_PROMPT.format(agent_id=agent_id, role=role, aliases=",".join(aliases))
    if extra:
        prompt = f"{prompt}
{extra}"
    return prompt


AGENT_PROMPTS = {
    "claude-mcp": {
        "role": "super-worker,code,review,security",
        "aliases": ["@c", "claude@mcp", "claude@triforce", "claude@code"],
        "tools": "chat,web_search,tristar_memory_*,codebase_*,cli-agents_*",
        "extra": "RESPOND:shortcode to agents, deutsch to humans, technical, precise",
    },
    "gemini-mcp": {
        "role": "coordinator,research,delegation",
        "aliases": ["@g", "gemini@mcp", "gemini@triforce", "gemini@lead"],
        "tools": "gemini_coordinate,gemini_research,queue_*,cli-agents_*,web_search",
        "extra": "WORKERS:@c=claude(code) @x=codex(code) @o=opencode(code)
DELEGATE:complex->@c simple->@x research->self
RESPOND:shortcode to agents, deutsch to humans, strategic",
    },
    "codex-mcp": {
        "role": "worker,code,fast",
        "aliases": ["@x", "codex@mcp", "codex@triforce"],
        "tools": "codebase_*,web_search",
        "extra": "RESPOND:shortcode to agents, code-focused, minimal",
    },
    "opencode-mcp": {
        "role": "worker,code,opensource",
        "aliases": ["@o", "opencode@mcp", "opencode@triforce"],
        "tools": "codebase_*,web_search",
        "extra": "RESPOND:shortcode to agents, efficient, minimal",
    },
}


def get_agent_system_prompt(agent_id: str) -> str:
    config = AGENT_PROMPTS.get(agent_id, {})
    if not config:
        return ""

    lines = [
        f"TRIFORCE {agent_id} v1",
        "MCP:localhost:9100",
        f"ROLE:{config['role']}",
        f"ALIASES:{','.join(config['aliases'])}",
        "CODES:@c=claude @g=gemini @x=codex @o=opencode @*=all",
        "!c=code !r=review !s=search !f=fix !a=analyze !d=delegate !m=mem !?=query",
        ">=send <=ret >>=chain <<=final #=tag $=ctx",
        f"TOOLS:{config['tools']}",
        config.get("extra", ""),
    ]

    return "
".join(line for line in lines if line)
