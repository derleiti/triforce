"""
System Control Service
======================

Provides capabilities to restart the backend, manage agents, and check system health
via MCP commands.

Features:
- Backend Restart (via sys.exit or systemd)
- Agent Restart (via AgentController)
- System Status
"""

import logging
import sys
import os
import asyncio
import signal
from typing import Dict, Any, Optional

logger = logging.getLogger("ailinux.system_control")

class SystemControlService:
    
    async def restart_backend(self, delay: int = 2) -> Dict[str, Any]:
        """
        Triggers a backend restart.
        
        Since the backend is usually managed by systemd or Docker, 
        the safest way to restart is to exit with a non-zero status code,
        triggering the supervisor to restart the process.
        """
        logger.warning(f"Backend restart requested via MCP. Exiting in {delay} seconds...")
        
        async def _restart_sequence():
            await asyncio.sleep(delay)
            logger.info("Exiting process now for restart.")
            # Exit with 1 to indicate error/restart need to systemd
            os._exit(1) 
            
        asyncio.create_task(_restart_sequence())
        
        return {
            "status": "initiated",
            "message": f"Backend restarting in {delay} seconds. Connection will be lost."
        }

    async def restart_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Restarts a specific CLI agent.
        """
        from .tristar.agent_controller import agent_controller
        
        try:
            # Check if agent exists
            agent = await agent_controller.get_agent(agent_id)
            if not agent:
                return {"status": "error", "error": f"Agent {agent_id} not found"}
                
            result = await agent_controller.restart_agent(agent_id)
            return {
                "status": "success", 
                "agent_id": agent_id,
                "details": result
            }
        except Exception as e:
            logger.error(f"Failed to restart agent {agent_id}: {e}")
            return {"status": "error", "error": str(e)}

    async def get_system_status(self) -> Dict[str, Any]:
        """
        Returns overview of system health.
        """
        from .tristar.agent_controller import agent_controller
        from .init_service import loadbalancer
        
        agents = await agent_controller.get_stats()
        lb_stats = loadbalancer.get_stats()
        
        return {
            "backend_pid": os.getpid(),
            "agents_active": agents["by_status"].get("running", 0),
            "agents_total": agents["total_agents"],
            "loadbalancer": lb_stats,
            "uptime": "TODO" # Could implement uptime tracking
        }

system_control = SystemControlService()
