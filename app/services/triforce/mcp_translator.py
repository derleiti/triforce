"""
MCP Translation Layer v2.60 - With RBAC and Audit

Parses @mcp.call() patterns from LLM output and executes them.

Pattern: @mcp.call(tool_name, {"param1": "value1", "param2": "value2"})
Result: [MCP_RESULT:tool_name] {"result": ...} or [MCP_ERROR:tool_name] {"error": ...}
"""

import re
import json
import time
from typing import List, Dict, Any, Optional, Tuple, Callable, Awaitable
from dataclasses import dataclass
import logging

from .rbac import rbac_service
from .audit_logger import audit_logger

logger = logging.getLogger("ailinux.triforce.mcp_translator")


@dataclass
class MCPCall:
    """Represents a parsed MCP call"""
    tool_name: str
    params: Dict[str, Any]
    raw_text: str
    line_number: int


@dataclass
class MCPResult:
    """Result of an MCP tool execution"""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str]
    execution_time_ms: float


class MCPParser:
    """Parses @mcp.call() patterns from text"""

    # Pattern matches: @mcp.call(tool_name, {json_params})
    MCP_PATTERN = re.compile(
        r'@mcp\.call\s*\(\s*(\w+)\s*,\s*(\{[^}]*\})\s*\)',
        re.MULTILINE | re.DOTALL
    )

    # Alternative pattern with single quotes
    MCP_PATTERN_ALT = re.compile(
        r"@mcp\.call\s*\(\s*(\w+)\s*,\s*(\{[^}]*\})\s*\)",
        re.MULTILINE | re.DOTALL
    )

    def parse(self, text: str) -> List[MCPCall]:
        """Parse all MCP calls from text"""
        calls = []
        lines = text.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Try main pattern
            for match in self.MCP_PATTERN.finditer(line):
                tool_name = match.group(1)
                params_str = match.group(2)

                try:
                    # Try standard JSON parse
                    params = json.loads(params_str)
                except json.JSONDecodeError:
                    # Try relaxed parsing
                    params = self._parse_relaxed(params_str)

                calls.append(MCPCall(
                    tool_name=tool_name,
                    params=params,
                    raw_text=match.group(0),
                    line_number=line_num
                ))

        return calls

    def _parse_relaxed(self, s: str) -> Dict[str, Any]:
        """Parse JSON-like string with relaxed rules"""
        result = {}

        # Remove braces
        s = s.strip().strip('{}')

        # Handle simple key: value pairs
        for pair in s.split(','):
            if ':' not in pair:
                continue

            key, value = pair.split(':', 1)
            key = key.strip().strip('"\'')
            value = value.strip()

            # Parse value
            if value.startswith('"') and value.endswith('"'):
                result[key] = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                result[key] = value[1:-1]
            elif value.lower() == 'true':
                result[key] = True
            elif value.lower() == 'false':
                result[key] = False
            elif value.lower() == 'null':
                result[key] = None
            else:
                try:
                    result[key] = int(value)
                except ValueError:
                    try:
                        result[key] = float(value)
                    except ValueError:
                        result[key] = value.strip('"\'')

        return result

    def has_mcp_calls(self, text: str) -> bool:
        """Check if text contains any MCP calls"""
        return bool(self.MCP_PATTERN.search(text))


class MCPExecutor:
    """Executes MCP tool calls with security checks"""

    def __init__(
        self,
        tools: Dict[str, Callable[..., Awaitable[Any]]],
        llm_id: str = "unknown",
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        self.tools = tools
        self.llm_id = llm_id
        self.session_id = session_id
        self.trace_id = trace_id

    async def execute(self, call: MCPCall) -> MCPResult:
        """Execute a single MCP call"""
        start_time = time.time()

        # 1. RBAC Check
        if not rbac_service.can_use_tool(self.llm_id, call.tool_name):
            await audit_logger.log_rbac_denied(
                llm_id=self.llm_id,
                tool_name=call.tool_name,
                required_permission=f"Permission for {call.tool_name}",
                trace_id=self.trace_id,
                session_id=self.session_id
            )
            return MCPResult(
                tool_name=call.tool_name,
                success=False,
                result=None,
                error=f"RBAC denied: {self.llm_id} cannot use {call.tool_name}",
                execution_time_ms=0
            )

        # 2. Check if tool exists
        if call.tool_name not in self.tools:
            return MCPResult(
                tool_name=call.tool_name,
                success=False,
                result=None,
                error=f"Unknown tool: {call.tool_name}",
                execution_time_ms=0
            )

        # 3. Execute the tool
        try:
            result = await self.tools[call.tool_name](**call.params)
            execution_time_ms = (time.time() - start_time) * 1000

            await audit_logger.log_tool_call(
                llm_id=self.llm_id,
                tool_name=call.tool_name,
                params=call.params,
                result_status="success",
                execution_time_ms=execution_time_ms,
                trace_id=self.trace_id,
                session_id=self.session_id
            )

            return MCPResult(
                tool_name=call.tool_name,
                success=True,
                result=result,
                error=None,
                execution_time_ms=execution_time_ms
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000

            await audit_logger.log_tool_call(
                llm_id=self.llm_id,
                tool_name=call.tool_name,
                params=call.params,
                result_status="error",
                execution_time_ms=execution_time_ms,
                trace_id=self.trace_id,
                session_id=self.session_id,
                error_message=str(e)
            )

            return MCPResult(
                tool_name=call.tool_name,
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=execution_time_ms
            )

    async def execute_all(self, calls: List[MCPCall]) -> List[MCPResult]:
        """Execute all MCP calls sequentially"""
        results = []
        for call in calls:
            result = await self.execute(call)
            results.append(result)
        return results


class MCPInjector:
    """Injects MCP results back into text"""

    def inject(
        self,
        text: str,
        calls: List[MCPCall],
        results: List[MCPResult]
    ) -> str:
        """Replace MCP calls with their results"""
        modified = text

        # Process in reverse order to maintain positions
        for call, result in sorted(
            zip(calls, results),
            key=lambda x: x[0].line_number,
            reverse=True
        ):
            if result.success:
                # Format successful result
                result_json = json.dumps(result.result, ensure_ascii=False, indent=2)
                replacement = f'[MCP_RESULT:{call.tool_name}] {result_json}'
            else:
                # Format error
                replacement = f'[MCP_ERROR:{call.tool_name}] {{"error": "{result.error}"}}'

            modified = modified.replace(call.raw_text, replacement)

        return modified


class MCPTranslator:
    """Main translator combining parser, executor, and injector"""

    def __init__(
        self,
        tools: Dict[str, Callable[..., Awaitable[Any]]],
        llm_id: str = "unknown",
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        self.parser = MCPParser()
        self.executor = MCPExecutor(tools, llm_id, session_id, trace_id)
        self.injector = MCPInjector()
        self.llm_id = llm_id
        self.session_id = session_id
        self.trace_id = trace_id

    async def process(self, text: str) -> Tuple[str, List[MCPResult]]:
        """
        Process text: parse MCP calls, execute them, inject results.

        Returns:
            Tuple of (modified_text, list_of_results)
        """
        calls = self.parser.parse(text)

        if not calls:
            return text, []

        results = await self.executor.execute_all(calls)
        modified = self.injector.inject(text, calls, results)

        return modified, results

    async def process_iterative(
        self,
        text: str,
        max_iterations: int = 5
    ) -> Tuple[str, List[MCPResult]]:
        """
        Process text iteratively until no more MCP calls.

        Some tools might generate new MCP calls in their output.
        This processes them iteratively up to max_iterations.

        Returns:
            Tuple of (final_text, all_results)
        """
        all_results = []
        current_text = text

        for iteration in range(max_iterations):
            calls = self.parser.parse(current_text)

            if not calls:
                break

            logger.debug(f"Iteration {iteration + 1}: Found {len(calls)} MCP calls")

            results = await self.executor.execute_all(calls)
            all_results.extend(results)
            current_text = self.injector.inject(current_text, calls, results)

        return current_text, all_results

    def has_pending_calls(self, text: str) -> bool:
        """Check if text has any pending MCP calls"""
        return self.parser.has_mcp_calls(text)


# Async MCP Processor for non-blocking execution
class AsyncMCPProcessor:
    """Async processor for handling MCP calls in streaming responses"""

    def __init__(
        self,
        tools: Dict[str, Callable[..., Awaitable[Any]]],
        llm_id: str = "unknown"
    ):
        self.tools = tools
        self.llm_id = llm_id
        self._pending_calls: List[MCPCall] = []
        self._results: List[MCPResult] = []
        self._buffer = ""

    def feed(self, chunk: str) -> Optional[str]:
        """
        Feed a text chunk and return processed output.

        Buffers incomplete MCP calls and processes complete ones.
        """
        self._buffer += chunk

        # Check for complete MCP calls
        parser = MCPParser()
        calls = parser.parse(self._buffer)

        if not calls:
            # No complete calls yet, return chunk as-is
            return chunk

        # We have calls - they'll be processed asynchronously
        self._pending_calls.extend(calls)

        # Return the chunk for now (will be replaced later)
        return chunk

    async def flush(self) -> Tuple[str, List[MCPResult]]:
        """Process all pending calls and return final text"""
        if not self._pending_calls:
            return self._buffer, []

        executor = MCPExecutor(self.tools, self.llm_id)
        results = await executor.execute_all(self._pending_calls)

        injector = MCPInjector()
        final_text = injector.inject(self._buffer, self._pending_calls, results)

        self._pending_calls.clear()
        self._buffer = ""

        return final_text, results


# Utility functions

def format_mcp_call(tool_name: str, params: Dict[str, Any]) -> str:
    """Format a tool call as MCP syntax"""
    params_json = json.dumps(params, ensure_ascii=False)
    return f'@mcp.call({tool_name}, {params_json})'


def format_mcp_result(tool_name: str, result: Any) -> str:
    """Format a result in MCP syntax"""
    result_json = json.dumps(result, ensure_ascii=False)
    return f'[MCP_RESULT:{tool_name}] {result_json}'


def format_mcp_error(tool_name: str, error: str) -> str:
    """Format an error in MCP syntax"""
    return f'[MCP_ERROR:{tool_name}] {{"error": "{error}"}}'
