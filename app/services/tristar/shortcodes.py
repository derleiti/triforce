"""
TriForce Shortcode Protocol v2.0
=================================
Token-effiziente Agent-Kommunikation mit erweiterten Pipeline-Features.

=== SYNTAX OVERVIEW ===

AGENT TARGETING:
    @agent              -> Target agent
    @gemini @claude @codex @mistral @deepseek @nova @*=all

ACTIONS (! prefix):
    !generate !gen !g   -> Generate content/code
    !review !r          -> Code review
    !search !s          -> Web/Memory search
    !code !c            -> Write code
    !fix !f             -> Debug/Fix
    !analyze !a         -> Analyze
    !delegate !d        -> Delegate to agent
    !memory !m          -> Memory store
    !query !?           -> Memory query
    !test !t            -> Run tests
    !patch !p           -> Patch/Edit file
    !execute !x         -> Execute code
    !explain !e         -> Explain
    !summarize !sum     -> Summarize

PIPELINE FLOW:
    >                   -> Send to target
    >>                  -> Chain (pass output to next)
    <                   -> Return result
    <<                  -> Final result
    |                   -> Pipe output
    @mcp>               -> Route through MCP server

OUTPUT CAPTURE:
    =[varname]          -> Store output in variable
    @[varname]          -> Reference stored variable
    [outputtoken]       -> Capture token count
    [prompt]            -> Generated prompt content
    [result]            -> Execution result

MODIFIERS:
    #tag                -> Add tag
    $context            -> Context variable
    !!!                 -> Critical priority
    !!                  -> High priority
    ~                   -> Low priority

=== EXAMPLES ===

@gemini>!generate[claudeprompt]@mcp>@claude>[outputtoken]
    -> Gemini generates prompt, sends via MCP to Claude, captures token count

@g>>@c !code "python script" #urgent !!
    -> Gemini chains to Claude with code task, urgent tag, high priority

@gemini>!search "latest news"=[results]>>@claude>!summarize @[results]
    -> Gemini searches, stores in $results, chains to Claude for summary

@*>!query "status"
    -> Broadcast query to all agents

@mistral>!review @[code] #security
    -> Mistral reviews code with security focus

Version: 2.0.0
"""

from typing import Dict, List, Optional, Any, Tuple
import re
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field

# Agent Aliases - alle Routen zu einem Agent
AGENT_ALIASES: Dict[str, str] = {
    # Claude
    "@c": "claude-mcp",
    "@claude": "claude-mcp",
    "claude@mcp": "claude-mcp",
    "claude@v1": "claude-mcp",
    "claude@triforce": "claude-mcp",
    "claude@code": "claude-mcp",

    # Gemini (Lead Coordinator)
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

    # Mistral (Reviewer)
    "@m": "mistral-mcp",
    "@mistral": "mistral-mcp",
    "mistral@mcp": "mistral-mcp",
    "mistral@v1": "mistral-mcp",
    "mistral@triforce": "mistral-mcp",
    "mistral@review": "mistral-mcp",

    # DeepSeek (Coder)
    "@d": "deepseek-mcp",
    "@deepseek": "deepseek-mcp",
    "deepseek@mcp": "deepseek-mcp",
    "deepseek@v1": "deepseek-mcp",
    "deepseek@triforce": "deepseek-mcp",
    "deepseek@code": "deepseek-mcp",

    # Nova (AILinux Custom)
    "@n": "nova-mcp",
    "@nova": "nova-mcp",
    "nova@mcp": "nova-mcp",
    "nova@v1": "nova-mcp",
    "nova@triforce": "nova-mcp",

    # MCP Server (für Pipeline-Routing)
    "@mcp": "mcp-server",
    "mcp@triforce": "mcp-server",
    "@triforce": "triforce-server",
    "@server": "triforce-server",

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
    "mistral-mcp": "@m",
    "deepseek-mcp": "@d",
    "nova-mcp": "@n",
    "mcp-server": "@mcp",
    "triforce-server": "@triforce",
    "broadcast": "@*",
}

# Action Codes - expanded v2
ACTIONS: Dict[str, str] = {
    # Generation
    "!generate": "generate",
    "!gen": "generate",
    "!g": "generate",

    # Code Operations
    "!code": "code",
    "!c": "code",
    "!fix": "fix",
    "!f": "fix",
    "!patch": "patch",
    "!p": "patch",
    "!execute": "execute",
    "!exec": "execute",
    "!x": "execute",
    "!test": "test",
    "!t": "test",

    # Review & Analysis
    "!review": "review",
    "!r": "review",
    "!analyze": "analyze",
    "!a": "analyze",
    "!explain": "explain",
    "!e": "explain",

    # Search & Memory
    "!search": "search",
    "!s": "search",
    "!memory": "memory",
    "!mem": "memory",
    "!m": "memory",
    "!query": "query",
    "!?": "query",

    # Delegation & Coordination
    "!delegate": "delegate",
    "!d": "delegate",
    "!coordinate": "coordinate",
    "!coord": "coordinate",

    # Content Operations
    "!summarize": "summarize",
    "!sum": "summarize",
    "!translate": "translate",
    "!trans": "translate",

    # System Operations
    "!status": "status",
    "!stat": "status",
    "!log": "log",
    "!sync": "sync",
    "!update": "update",
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
        prompt = f"{prompt}\n{extra}"
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
        "extra": "WORKERS:@c=claude(code) @x=codex(code) @o=opencode(code)\nDELEGATE:complex->@c simple->@x research->self\nRESPOND:shortcode to agents, deutsch to humans, strategic",
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
        f"TRIFORCE {agent_id} v2",
        "MCP:localhost:9100",
        f"ROLE:{config['role']}",
        f"ALIASES:{','.join(config['aliases'])}",
        "AGENTS:@c=claude @g=gemini @x=codex @o=opencode @m=mistral @d=deepseek @n=nova @*=all @mcp=server",
        "ACTIONS:!g=generate !c=code !r=review !s=search !f=fix !a=analyze !d=delegate !m=mem !?=query !x=exec !t=test !e=explain !sum=summarize",
        "FLOW:>=send <=ret >>=chain <<=final |=pipe",
        "OUTPUT:=[var] @[var] [outputtoken] [prompt] [result]",
        "PRIORITY:!!!=critical !!=high ~=low #=tag $=ctx",
        f"TOOLS:{config['tools']}",
        config.get("extra", ""),
    ]

    return "\n".join(line for line in lines if line)


# ============================================================================
# PIPELINE PARSER v2.0 - Erweiterte Shortcode-Sprache
# ============================================================================

@dataclass
class PipelineStep:
    """Ein Schritt in einer Shortcode-Pipeline"""
    source: Optional[str] = None
    target: Optional[str] = None
    action: Optional[str] = None
    content: str = ""
    output_var: Optional[str] = None      # =[varname]
    input_var: Optional[str] = None       # @[varname]
    capture_tokens: bool = False          # [outputtoken]
    capture_prompt: bool = False          # [prompt]
    capture_result: bool = False          # [result]
    flow: str = "send"                    # send, chain, return, final, pipe
    tags: List[str] = field(default_factory=list)
    priority: str = "normal"
    via_mcp: bool = False                 # @mcp> routing

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "action": self.action,
            "content": self.content,
            "output_var": self.output_var,
            "input_var": self.input_var,
            "capture_tokens": self.capture_tokens,
            "capture_prompt": self.capture_prompt,
            "capture_result": self.capture_result,
            "flow": self.flow,
            "tags": self.tags,
            "priority": self.priority,
            "via_mcp": self.via_mcp,
        }


@dataclass
class ShortcodePipeline:
    """Eine vollständige Shortcode-Pipeline mit mehreren Steps"""
    raw: str
    steps: List[PipelineStep] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    is_valid: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw,
            "steps": [s.to_dict() for s in self.steps],
            "variables": self.variables,
            "is_valid": self.is_valid,
            "error": self.error,
        }


class PipelineParser:
    """
    Parser für erweiterte Shortcode-Pipelines.

    Beispiele:
        @gemini>!generate[claudeprompt]@mcp>@claude>[outputtoken]
        @g>>@c !code "hello" #urgent !!
        @gemini>!search "news"=[results]>>@claude>!summarize @[results]
    """

    # Regex patterns
    AGENT_PATTERN = re.compile(r'@(\w+)')
    ACTION_PATTERN = re.compile(r'!(\w+)')
    OUTPUT_VAR_PATTERN = re.compile(r'=\[(\w+)\]')
    INPUT_VAR_PATTERN = re.compile(r'@\[(\w+)\]')
    CAPTURE_PATTERN = re.compile(r'\[(outputtoken|prompt|result)\]')
    FLOW_PATTERN = re.compile(r'(>>|<<|>|<|\|)')
    TAG_PATTERN = re.compile(r'#(\w+)')
    PRIORITY_PATTERN = re.compile(r'(!!!|!!|~)')
    QUOTED_PATTERN = re.compile(r'"([^"]*)"')

    # Pipeline step separator
    STEP_SEPARATORS = ['>>@', '>@', '|@']

    def parse(self, shortcode: str) -> ShortcodePipeline:
        """Parse einen Shortcode-String in eine Pipeline"""
        pipeline = ShortcodePipeline(raw=shortcode)

        if not shortcode or not shortcode.strip():
            pipeline.is_valid = False
            pipeline.error = "Empty shortcode"
            return pipeline

        shortcode = shortcode.strip()

        # Split by pipeline separators
        segments = self._split_pipeline(shortcode)

        for segment in segments:
            step = self._parse_step(segment)
            if step:
                pipeline.steps.append(step)

        if not pipeline.steps:
            pipeline.is_valid = False
            pipeline.error = "No valid steps found"

        return pipeline

    def _split_pipeline(self, shortcode: str) -> List[str]:
        """Split pipeline into individual steps"""
        # Replace separators with unique marker
        marker = "|||STEP|||"
        result = shortcode

        for sep in self.STEP_SEPARATORS:
            result = result.replace(sep, f"{marker}@")

        segments = result.split(marker)
        return [s.strip() for s in segments if s.strip()]

    def _parse_step(self, segment: str) -> Optional[PipelineStep]:
        """Parse einen einzelnen Pipeline-Step"""
        step = PipelineStep()

        # Extract @mcp routing
        if '@mcp>' in segment.lower() or '@mcp' in segment.lower():
            step.via_mcp = True
            segment = segment.replace('@mcp>', '').replace('@MCP>', '')

        # Extract quoted content first
        quoted = self.QUOTED_PATTERN.findall(segment)
        if quoted:
            step.content = quoted[0]
            segment = self.QUOTED_PATTERN.sub('', segment)

        # Extract output variable =[var]
        output_match = self.OUTPUT_VAR_PATTERN.search(segment)
        if output_match:
            step.output_var = output_match.group(1)
            segment = self.OUTPUT_VAR_PATTERN.sub('', segment)

        # Extract input variable @[var]
        input_match = self.INPUT_VAR_PATTERN.search(segment)
        if input_match:
            step.input_var = input_match.group(1)
            segment = self.INPUT_VAR_PATTERN.sub('', segment)

        # Extract capture flags
        for capture_match in self.CAPTURE_PATTERN.finditer(segment):
            capture_type = capture_match.group(1)
            if capture_type == "outputtoken":
                step.capture_tokens = True
            elif capture_type == "prompt":
                step.capture_prompt = True
            elif capture_type == "result":
                step.capture_result = True
        segment = self.CAPTURE_PATTERN.sub('', segment)

        # Extract flow
        flow_match = self.FLOW_PATTERN.search(segment)
        if flow_match:
            flow_symbol = flow_match.group(1)
            step.flow = FLOW.get(flow_symbol, "send")

        # Extract agents
        agents = self.AGENT_PATTERN.findall(segment)
        if agents:
            # First agent is source, second is target (if flow present)
            step.source = resolve_agent(f"@{agents[0]}")
            if len(agents) > 1:
                step.target = resolve_agent(f"@{agents[1]}")
            elif step.flow in ["send", "chain"]:
                # If only one agent and flow is send/chain, it's the target
                step.target = step.source
                step.source = None

        # Extract action
        action_match = self.ACTION_PATTERN.search(segment)
        if action_match:
            action_code = f"!{action_match.group(1)}"
            step.action = ACTIONS.get(action_code, action_match.group(1))

        # Extract tags
        step.tags = self.TAG_PATTERN.findall(segment)

        # Extract priority
        priority_match = self.PRIORITY_PATTERN.search(segment)
        if priority_match:
            step.priority = PRIORITY.get(priority_match.group(1), "normal")

        # If no content from quotes, get remaining text
        if not step.content:
            # Remove all parsed elements
            remaining = segment
            remaining = self.AGENT_PATTERN.sub('', remaining)
            remaining = self.ACTION_PATTERN.sub('', remaining)
            remaining = self.FLOW_PATTERN.sub('', remaining)
            remaining = self.TAG_PATTERN.sub('', remaining)
            remaining = self.PRIORITY_PATTERN.sub('', remaining)
            step.content = remaining.strip()

        return step if (step.source or step.target or step.action) else None

    def expand_to_human(self, pipeline: ShortcodePipeline) -> str:
        """Expandiert Pipeline in menschenlesbare Form"""
        if not pipeline.is_valid:
            return f"[INVALID: {pipeline.error}]"

        parts = []
        for i, step in enumerate(pipeline.steps, 1):
            step_desc = []

            if step.source:
                step_desc.append(f"[{step.source}]")
            if step.flow:
                step_desc.append(f"--{step.flow}-->")
            if step.target:
                step_desc.append(f"[{step.target}]")
            if step.action:
                step_desc.append(f"ACTION:{step.action}")
            if step.content:
                step_desc.append(f'"{step.content}"')
            if step.output_var:
                step_desc.append(f"STORE_IN:{step.output_var}")
            if step.input_var:
                step_desc.append(f"USE:{step.input_var}")
            if step.capture_tokens:
                step_desc.append("[CAPTURE_TOKENS]")
            if step.tags:
                step_desc.append(f"TAGS:{','.join(step.tags)}")
            if step.priority != "normal":
                step_desc.append(f"PRIORITY:{step.priority}")
            if step.via_mcp:
                step_desc.append("[VIA_MCP]")

            parts.append(f"Step {i}: {' '.join(step_desc)}")

        return "\n".join(parts)


# Singleton parser
pipeline_parser = PipelineParser()


# ============================================================================
# AUTO-DECODE DOKUMENTATION
# ============================================================================

SHORTCODE_DOCUMENTATION = """
# TriForce Shortcode Protocol v2.0
## Token-effiziente Agent-Kommunikation

### AGENT ALIASES
| Kurz | Lang | Agent ID |
|------|------|----------|
| @c | @claude | claude-mcp |
| @g | @gemini | gemini-mcp (Lead) |
| @x | @codex | codex-mcp |
| @o | @opencode | opencode-mcp |
| @m | @mistral | mistral-mcp (Reviewer) |
| @d | @deepseek | deepseek-mcp |
| @n | @nova | nova-mcp |
| @mcp | @triforce | mcp-server |
| @* | @all | broadcast |

### AKTIONEN (! Prefix)
| Code | Aktion | Beschreibung |
|------|--------|--------------|
| !g, !gen | generate | Inhalt generieren |
| !c, !code | code | Code schreiben |
| !r, !review | review | Code-Review |
| !s, !search | search | Web/Memory-Suche |
| !f, !fix | fix | Fehler beheben |
| !a, !analyze | analyze | Analysieren |
| !d, !delegate | delegate | Delegieren |
| !m, !mem | memory | Memory speichern |
| !? | query | Memory abfragen |
| !x, !exec | execute | Code ausführen |
| !t, !test | test | Tests ausführen |
| !e, !explain | explain | Erklären |
| !sum | summarize | Zusammenfassen |

### PIPELINE FLOW
| Symbol | Bedeutung |
|--------|-----------|
| > | Senden an Ziel |
| >> | Verketten (Output weiterleiten) |
| < | Antwort zurückgeben |
| << | Finale Antwort |
| | | Output pipen |
| @mcp> | Über MCP Server routen |

### OUTPUT CAPTURE
| Syntax | Beschreibung |
|--------|--------------|
| =[var] | Output in Variable speichern |
| @[var] | Variable verwenden |
| [outputtoken] | Token-Anzahl erfassen |
| [prompt] | Generierten Prompt erfassen |
| [result] | Ergebnis erfassen |

### MODIFIKATOREN
| Syntax | Bedeutung |
|--------|-----------|
| #tag | Tag hinzufügen |
| $ctx | Kontext-Variable |
| !!! | Kritische Priorität |
| !! | Hohe Priorität |
| ~ | Niedrige Priorität |

### BEISPIELE

```
# Gemini generiert Prompt für Claude, sendet über MCP
@gemini>!generate[claudeprompt]@mcp>@claude>[outputtoken]

# Gemini delegiert Code-Task an Claude mit hoher Priorität
@g>>@c !code "python script" #urgent !!

# Pipeline: Suchen -> Speichern -> Zusammenfassen
@gemini>!search "latest news"=[results]>>@claude>!summarize @[results]

# Broadcast Status-Abfrage an alle
@*>!query "status"

# Mistral reviewt Code mit Security-Focus
@mistral>!review @[code] #security

# Claude schreibt Code, DeepSeek optimiert
@c>!code "sort algorithm"=[code]>>@d>!fix @[code] #optimize
```

### MCP SERVER BEFEHLE

Der MCP Server unter `/mcp/`, `/v1/`, `/triforce/` versteht:

| Endpoint | Beschreibung |
|----------|--------------|
| /init | Shortcode-Dokumentation + Auto-Decode |
| /tools | Verfügbare MCP Tools |
| /mesh/* | Mesh AI Orchestration |
| /queue/* | Command Queue |

### AUTO-UPDATE FEATURE

Der MCP Server sendet automatisch Updates an Gemini:
```
@gemini>![outputtoken] SYNC:changes={count}
```

Dies hält Gemini als Lead-Koordinator auf dem Laufenden über:
- Neue Tasks im System
- Abgeschlossene Operationen
- Queue-Status
- Agent-Aktivitäten
"""


def get_shortcode_documentation() -> str:
    """Gibt die vollständige Shortcode-Dokumentation zurück"""
    return SHORTCODE_DOCUMENTATION


def auto_decode_shortcode(shortcode: str) -> Dict[str, Any]:
    """
    Decodiert einen Shortcode und gibt strukturierte Informationen zurück.

    Returns:
        {
            "raw": str,
            "decoded": {...},
            "human_readable": str,
            "is_valid": bool,
            "error": Optional[str]
        }
    """
    pipeline = pipeline_parser.parse(shortcode)

    return {
        "raw": shortcode,
        "decoded": pipeline.to_dict(),
        "human_readable": pipeline_parser.expand_to_human(pipeline),
        "is_valid": pipeline.is_valid,
        "error": pipeline.error,
    }
