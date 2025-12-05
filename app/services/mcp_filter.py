"""
MCP Command Filter Service
==========================

Filters and executes MCP/API commands from chat messages.
Allows non-MCP models to access API functionality transparently.

Features:
- Detects @mcp.call() patterns in text
- Detects /api, /mcp, /v1, /triforce commands
- Executes commands and injects results
- Supports web search for unknown queries
- Logs ALL detected commands to TriForce Central Logger

Version: 2.81 - Central Logging Integration
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ailinux.mcp_filter")

# TriForce Central Logger Integration
try:
    from ..utils.triforce_logging import central_logger
    _HAS_CENTRAL_LOGGING = True
except ImportError:
    _HAS_CENTRAL_LOGGING = False
    central_logger = None

# Pattern für MCP-Aufrufe
MCP_CALL_PATTERN = re.compile(
    r'@mcp\.call\s*\(\s*([a-zA-Z0-9_.\-]+)\s*,?\s*(\{[^}]*\})?\s*\)',
    re.IGNORECASE | re.DOTALL
)

# Pattern für Slash-Kommandos
SLASH_COMMAND_PATTERN = re.compile(
    r'(?:^|\s)/(mcp|api|v1|triforce|ollama|tristar)\s+(\S+)(?:\s+(.*))?',
    re.IGNORECASE | re.MULTILINE
)

# Pattern für direkte API-Anfragen
API_REQUEST_PATTERN = re.compile(
    r'(?:GET|POST|PUT|DELETE)\s+((?:/v1|/mcp|/triforce)[^\s]+)',
    re.IGNORECASE
)

# Pattern für natürlichsprachliche Anfragen
NATURAL_API_PATTERNS = [
    (re.compile(r'(?:list|show|get)\s+(?:all\s+)?(?:ollama\s+)?models?', re.I), 'ollama.list', {}),
    (re.compile(r'(?:list|show|get)\s+(?:running|active)\s+models?', re.I), 'ollama.ps', {}),
    (re.compile(r'pull\s+(?:model\s+)?([a-zA-Z0-9.:_-]+)', re.I), 'ollama.pull', lambda m: {'name': m.group(1)}),
    (re.compile(r'(?:show|info|details?)\s+(?:model\s+)?([a-zA-Z0-9.:_-]+)', re.I), 'ollama.show', lambda m: {'name': m.group(1)}),
    (re.compile(r'(?:delete|remove)\s+(?:model\s+)?([a-zA-Z0-9.:_-]+)', re.I), 'ollama.delete', lambda m: {'name': m.group(1)}),
    (re.compile(r'(?:list|show|get)\s+(?:all\s+)?prompts?', re.I), 'tristar.prompts.list', {}),
    (re.compile(r'(?:list|show|get)\s+(?:all\s+)?agents?', re.I), 'tristar.agents', {}),
    (re.compile(r'(?:system|tristar)\s+status', re.I), 'tristar.status', {}),
    (re.compile(r'(?:get|show|read)\s+logs?(?:\s+for\s+(\S+))?', re.I), 'tristar.logs', lambda m: {'agent_id': m.group(1)} if m.group(1) else {}),
    (re.compile(r'(?:get|show|read)\s+settings?', re.I), 'tristar.settings', {}),
    (re.compile(r'ollama\s+health', re.I), 'ollama.health', {}),
]


class MCPFilter:
    """Filters MCP commands from chat and executes them."""

    def __init__(self):
        self._handlers = None

    async def _get_handlers(self) -> Dict[str, Any]:
        """Lazy load handlers to avoid circular imports."""
        if self._handlers is None:
            from ..routes.mcp_remote import TOOL_HANDLERS
            self._handlers = TOOL_HANDLERS
        return self._handlers

    def extract_mcp_calls(self, text: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        Extract MCP calls from text.

        Returns: List of (full_match, tool_name, arguments)
        """
        calls = []

        # @mcp.call() patterns
        for match in MCP_CALL_PATTERN.finditer(text):
            tool_name = match.group(1)
            args_str = match.group(2) or '{}'
            try:
                args = json.loads(args_str)
            except json.JSONDecodeError:
                args = {}
            calls.append((match.group(0), tool_name, args))

        # Slash commands: /mcp ollama.list, /triforce status, etc.
        for match in SLASH_COMMAND_PATTERN.finditer(text):
            prefix = match.group(1).lower()
            command = match.group(2)
            extra = match.group(3) or ''

            # Build tool name
            if prefix == 'mcp':
                tool_name = command
            elif prefix == 'ollama':
                tool_name = f'ollama.{command}'
            elif prefix == 'tristar':
                tool_name = f'tristar.{command}'
            else:
                tool_name = command

            # Parse extra as JSON or key=value pairs
            args = {}
            if extra:
                extra = extra.strip()
                if extra.startswith('{'):
                    try:
                        args = json.loads(extra)
                    except json.JSONDecodeError:
                        pass
                else:
                    # key=value pairs
                    for part in extra.split():
                        if '=' in part:
                            k, v = part.split('=', 1)
                            args[k] = v

            calls.append((match.group(0), tool_name, args))

        # Natural language patterns
        for pattern, tool_name, args_builder in NATURAL_API_PATTERNS:
            match = pattern.search(text)
            if match:
                if callable(args_builder):
                    args = args_builder(match)
                else:
                    args = args_builder
                calls.append((match.group(0), tool_name, args))

        return calls

    async def execute_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single MCP tool call."""
        handlers = await self._get_handlers()

        handler = handlers.get(tool_name)
        if not handler:
            # Try with prefixes
            for prefix in ['ollama.', 'tristar.', 'codebase.', 'cli-agents.']:
                handler = handlers.get(f'{prefix}{tool_name}')
                if handler:
                    break

        if not handler:
            return {
                'error': f"Tool '{tool_name}' not found",
                'available_tools': list(handlers.keys())[:20],
            }

        try:
            result = await handler(arguments)
            return {'tool': tool_name, 'result': result, 'success': True}
        except Exception as e:
            logger.error(f"MCP call failed: {tool_name} - {e}")
            return {'tool': tool_name, 'error': str(e), 'success': False}

    async def process_message(
        self,
        message: str,
        execute: bool = True,
        inject_results: bool = True,
        source: str = "chat",
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Process a message, extract and optionally execute MCP calls.
        ALL detected commands are logged to TriForce Central Logger for
        idle agents to process.

        Args:
            message: The input message
            execute: Whether to execute the calls
            inject_results: Whether to inject results into the message
            source: Source identifier (user, mesh-ai, agent-id)

        Returns:
            (processed_message, results)
        """
        calls = self.extract_mcp_calls(message)

        if not calls:
            return message, []

        results = []
        processed = message

        for full_match, tool_name, args in calls:
            # ===== CENTRAL LOGGING - Log ALL detected commands =====
            if _HAS_CENTRAL_LOGGING and central_logger:
                await central_logger.log(
                    category="mcp_call",
                    message=f"MCP Command detected: {tool_name}",
                    level="info",
                    source=f"mcp_filter:{source}",
                    metadata={
                        "tool": tool_name,
                        "arguments": args,
                        "full_match": full_match,
                        "execute": execute,
                        "source": source,
                        "pending": not execute,  # If not executed, mark as pending for idle agents
                    }
                )

            if execute:
                result = await self.execute_call(tool_name, args)
                results.append(result)

                # Log execution result
                if _HAS_CENTRAL_LOGGING and central_logger:
                    await central_logger.log(
                        category="mcp_call",
                        message=f"MCP Command executed: {tool_name} -> {'success' if result.get('success') else 'error'}",
                        level="info" if result.get('success') else "warning",
                        source=f"mcp_filter:{source}",
                        metadata={
                            "tool": tool_name,
                            "success": result.get('success', False),
                            "error": result.get('error'),
                        }
                    )

                if inject_results:
                    # Replace the call with the result
                    if result.get('success'):
                        result_text = f"\n[MCP_RESULT:{tool_name}]\n```json\n{json.dumps(result.get('result', {}), indent=2, ensure_ascii=False)}\n```\n"
                    else:
                        result_text = f"\n[MCP_ERROR:{tool_name}] {result.get('error', 'Unknown error')}\n"
                    processed = processed.replace(full_match, result_text, 1)
            else:
                # Just mark as detected (logged above with pending=True)
                results.append({'tool': tool_name, 'args': args, 'detected': True})

        return processed, results

    def filter_mcp_from_display(self, text: str) -> str:
        """
        Remove MCP calls from text for display purposes.
        The calls are still tracked but not shown to users.
        """
        # Remove @mcp.call() patterns
        text = MCP_CALL_PATTERN.sub('', text)

        # Remove slash commands
        text = SLASH_COMMAND_PATTERN.sub('', text)

        # Remove [MCP_RESULT:...] blocks
        text = re.sub(r'\[MCP_RESULT:[^\]]+\].*?```\s*', '', text, flags=re.DOTALL)

        # Remove [MCP_ERROR:...] lines
        text = re.sub(r'\[MCP_ERROR:[^\]]+\][^\n]*\n?', '', text)

        # Clean up multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    async def enhance_with_api_data(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Enhance a message with relevant API data.
        Detects questions about the system and fetches relevant info.
        """
        enhancements = []

        # Check for questions about models
        if re.search(r'(?:which|what|list|available)\s+models?', message, re.I):
            result = await self.execute_call('ollama.list', {})
            if result.get('success'):
                models = result.get('result', {}).get('models', [])
                model_names = [m.get('name') for m in models[:10]]
                enhancements.append(f"[System Info: Available models: {', '.join(model_names)}]")

        # Check for questions about system status
        if re.search(r'(?:system|tristar|backend)\s+(?:status|health)', message, re.I):
            result = await self.execute_call('tristar.status', {})
            if result.get('success'):
                status = result.get('result', {})
                services = status.get('services', {})
                active = [k for k, v in services.items() if v == 'active']
                enhancements.append(f"[System Info: Active services: {', '.join(active)}]")

        # Check for questions about agents
        if re.search(r'(?:which|what|list|available)\s+agents?', message, re.I):
            result = await self.execute_call('tristar.agents', {})
            if result.get('success'):
                agents = result.get('result', {}).get('agents', [])
                agent_ids = [a.get('id', 'unknown') for a in agents[:10]]
                enhancements.append(f"[System Info: Configured agents: {', '.join(agent_ids)}]")

        if enhancements:
            return message + '\n\n' + '\n'.join(enhancements)

        return message


# Singleton instance
mcp_filter = MCPFilter()


# ============================================================================
# Convenience functions
# ============================================================================

async def filter_and_execute(message: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Process message and execute MCP calls."""
    return await mcp_filter.process_message(message)


def remove_mcp_display(text: str) -> str:
    """Remove MCP commands from display text."""
    return mcp_filter.filter_mcp_from_display(text)


async def enhance_message(message: str) -> str:
    """Enhance message with API data."""
    return await mcp_filter.enhance_with_api_data(message)
