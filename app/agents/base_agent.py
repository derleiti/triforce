"""
TriStar Base Agent v2.80

Base class for all TriStar LLM agents.
Provides common functionality for agent initialization, MCP communication, and lifecycle management.
"""

import asyncio
import argparse
import logging
import signal
import sys
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

import httpx

logger = logging.getLogger("ailinux.tristar.agent")


@dataclass
class AgentConfig:
    """Agent configuration"""
    agent_id: str
    role: str  # admin, lead, worker, reviewer
    # Use localhost for internal API calls (no internet required)
    api_base: str = "http://localhost:9100/v1"
    system_prompt: str = ""
    append_system_prompt: str = ""
    workspace_dir: str = "/var/tristar/agents"
    log_level: str = "INFO"
    heartbeat_interval: int = 30
    max_retries: int = 3


class BaseAgent:
    """
    Base class for TriStar agents.

    Provides:
    - MCP protocol handling
    - API communication
    - Lifecycle management
    - Heartbeat/health monitoring
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = config.agent_id
        self.role = config.role
        self.api_base = config.api_base.rstrip("/")

        # Build full system prompt
        self.system_prompt = config.system_prompt
        if config.append_system_prompt:
            self.system_prompt += "\n\n" + config.append_system_prompt

        # Workspace
        self.workspace = Path(config.workspace_dir) / config.agent_id
        self.workspace.mkdir(parents=True, exist_ok=True)

        # State
        self._running = False
        self._client: Optional[httpx.AsyncClient] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Setup logging
        logging.basicConfig(
            level=getattr(logging, config.log_level),
            format=f"%(asctime)s [{self.agent_id}] %(levelname)s: %(message)s"
        )

    async def start(self):
        """Start the agent"""
        logger.info(f"Starting {self.agent_id} agent (role: {self.role})")

        self._running = True
        self._client = httpx.AsyncClient(timeout=120)

        # Register with TriStar
        await self._register()

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Setup signal handlers
        for sig in (signal.SIGINT, signal.SIGTERM):
            asyncio.get_event_loop().add_signal_handler(
                sig, lambda: asyncio.create_task(self.stop())
            )

        logger.info(f"Agent {self.agent_id} started successfully")

        # Run main loop
        await self._main_loop()

    async def stop(self):
        """Stop the agent"""
        logger.info(f"Stopping {self.agent_id} agent")
        self._running = False

        # Cancel heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Unregister
        await self._unregister()

        # Close client
        if self._client:
            await self._client.aclose()

        logger.info(f"Agent {self.agent_id} stopped")

    async def _register(self):
        """Register agent with TriStar"""
        try:
            # Initialize session
            response = await self._client.post(
                f"{self.api_base}/triforce/init",
                json={
                    "request": "status",
                    "llm_id": self.agent_id,
                }
            )
            if response.status_code == 200:
                logger.info(f"Registered with TriStar: {response.json()}")
        except Exception as e:
            logger.warning(f"Failed to register: {e}")

    async def _unregister(self):
        """Unregister agent from TriStar"""
        try:
            # Log disconnection
            await self._client.post(
                f"{self.api_base}/triforce/audit/log",
                json={
                    "llm_id": self.agent_id,
                    "action": "agent_disconnect",
                    "level": "info",
                }
            )
        except Exception:
            pass

    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self._running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                await self._send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")

    async def _send_heartbeat(self):
        """Send heartbeat to TriStar"""
        try:
            response = await self._client.get(
                f"{self.api_base}/triforce/health"
            )
            if response.status_code != 200:
                logger.warning(f"Heartbeat unhealthy: {response.status_code}")
        except Exception as e:
            logger.warning(f"Heartbeat error: {e}")

    async def _main_loop(self):
        """Main agent loop - override in subclasses"""
        while self._running:
            try:
                # Poll for tasks
                task = await self._poll_for_tasks()
                if task:
                    await self._process_task(task)
                else:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)

    async def _poll_for_tasks(self) -> Optional[Dict[str, Any]]:
        """Poll TriStar for pending tasks"""
        # This would be implemented with a task queue
        # For now, agents are called directly via the mesh
        return None

    async def _process_task(self, task: Dict[str, Any]):
        """Process a task - override in subclasses"""
        logger.info(f"Processing task: {task.get('task_id')}")

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool"""
        try:
            # Route to appropriate endpoint
            if tool_name.startswith("memory_"):
                endpoint = f"/triforce/memory/{tool_name.replace('memory_', '')}"
            elif tool_name.startswith("llm_"):
                endpoint = f"/triforce/mesh/{tool_name.replace('llm_', '')}"
            elif tool_name.startswith("file_"):
                endpoint = f"/triforce/workspace/{tool_name}"
            else:
                endpoint = f"/triforce/tools/{tool_name}"

            response = await self._client.post(
                f"{self.api_base}{endpoint}",
                json=params
            )

            return response.json()

        except Exception as e:
            return {"error": str(e)}

    async def call_llm(
        self,
        target: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call another LLM in the mesh"""
        return await self.call_tool("llm_call", {
            "target": target,
            "prompt": prompt,
            "caller_llm": self.agent_id,
            "context": context,
        })

    async def store_memory(
        self,
        content: str,
        memory_type: str,
        confidence: float = 0.8,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Store information in memory"""
        return await self.call_tool("memory_store", {
            "content": content,
            "type": memory_type,
            "confidence": confidence,
            "tags": tags or [],
            "source_llm": self.agent_id,
        })

    async def recall_memory(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.5
    ) -> Dict[str, Any]:
        """Recall from memory"""
        return await self.call_tool("memory_recall", {
            "query": query,
            "limit": limit,
            "min_confidence": min_confidence,
        })

    def log_to_workspace(self, message: str, level: str = "info"):
        """Log message to workspace file"""
        log_file = self.workspace / "agent.log"
        timestamp = datetime.utcnow().isoformat()
        with open(log_file, "a") as f:
            f.write(f"{timestamp} [{level.upper()}] {message}\n")


def create_agent_from_args() -> BaseAgent:
    """Create agent from command line arguments"""
    parser = argparse.ArgumentParser(description="TriStar Agent")
    parser.add_argument("--agent-id", required=True, help="Agent ID")
    parser.add_argument("--role", required=True, help="Agent role")
    parser.add_argument("--api-base", default="http://localhost:9100/v1", help="API base URL")
    parser.add_argument("--system-prompt", default="", help="System prompt (inline or file path)")
    parser.add_argument("--system-prompt-file", default="", help="Path to system prompt file")
    parser.add_argument("--append-system-prompt", default="", help="Additional system prompt")
    parser.add_argument("--append-system-prompt-file", default="", help="Path to additional prompt file")
    parser.add_argument("--workspace-dir", default="/var/tristar/agents", help="Workspace directory")
    parser.add_argument("--log-level", default="INFO", help="Log level")

    args = parser.parse_args()

    # Load system prompt from file if specified
    system_prompt = args.system_prompt
    if args.system_prompt_file:
        try:
            with open(args.system_prompt_file, "r") as f:
                system_prompt = f.read().strip()
        except Exception:
            pass

    # Load append prompt from file if specified
    append_prompt = args.append_system_prompt
    if args.append_system_prompt_file:
        try:
            with open(args.append_system_prompt_file, "r") as f:
                append_prompt = f.read().strip()
        except Exception:
            pass

    config = AgentConfig(
        agent_id=args.agent_id,
        role=args.role,
        api_base=args.api_base,
        system_prompt=system_prompt,
        append_system_prompt=append_prompt,
        workspace_dir=args.workspace_dir,
        log_level=args.log_level,
    )

    return BaseAgent(config)


async def main():
    """Main entry point"""
    agent = create_agent_from_args()
    await agent.start()


if __name__ == "__main__":
    asyncio.run(main())
