"""
TriStar Gemini Lead Agent v2.80

Lead agent for chain orchestration.
Responsibilities: Planning, task decomposition, consolidation
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, Optional, List

from .base_agent import BaseAgent, AgentConfig, create_agent_from_args

logger = logging.getLogger("ailinux.gemini_lead")


class GeminiLeadAgent(BaseAgent):
    """
    Gemini Lead Agent - Primary orchestrator for chains.

    Capabilities:
    - Chain planning and task decomposition
    - Agent coordination
    - Result consolidation
    - Quality assessment
    """

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.active_chains: Dict[str, Any] = {}

    async def plan_chain(self, user_prompt: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a lightweight chain plan via Gemini without heavy orchestration.

        Takes the user prompt plus optional context, asks Gemini for a JSON plan,
        and returns parsed tasks, agent assignments, and rough cycle estimates.
        """
        from ..services.gemini_access import gemini_access
        
        prompt = f"""Plan a robust execution chain for: {user_prompt}
Context: {context or 'None'}

Return JSON with keys: plan (string), tasks (array), agent_assignments (object), estimated_cycles (int)."""

        try:
            response = await gemini_access.process_request(
                prompt, 
                research=False, 
                store_findings=False,
                include_context=False,
            )

            plan_text = response.get("response", "") or ""
            parsed_plan: Optional[Dict[str, Any]] = None
            try:
                parsed_plan = json.loads(plan_text)
            except json.JSONDecodeError:
                match = re.search(r"(\\{.*\\}|\\[.*\\])", plan_text, re.DOTALL)
                if match:
                    try:
                        parsed_plan = json.loads(match.group(1))
                    except json.JSONDecodeError as exc:
                        logger.warning("Failed to parse Gemini plan JSON: %s", exc)
                else:
                    logger.warning("Failed to parse Gemini plan JSON; returning raw text")
            
            return {
                "plan": (parsed_plan.get("plan") if isinstance(parsed_plan, dict) else plan_text) or "No plan generated",
                "tasks": parsed_plan.get("tasks", []) if isinstance(parsed_plan, dict) else [],
                "agent_assignments": parsed_plan.get("agent_assignments", {}) if isinstance(parsed_plan, dict) else {}, 
                "estimated_cycles": parsed_plan.get("estimated_cycles", 1) if isinstance(parsed_plan, dict) else 1,
                "metadata": {
                    "raw_response": plan_text,
                    "research": response.get("research", {}),
                }
            }
        except Exception as e:
            logger.error("Plan chain failed: %s", e, exc_info=True)
            return {"error": str(e), "plan": "Failed to generate plan"}

    async def consolidate_results(
        self,
        chain_id: str,
        agent_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Consolidate raw agent outputs into a concise, consistent summary.

        Gemini receives the chain id and up to the first ~2000 characters of
        agent outputs, then proposes a merged summary and refinement hint.
        """
        from ..services.gemini_access import gemini_access

        result: Dict[str, Any] = {
            "consolidated": False,
            "summary": "",
            "needs_refinement": False,
        }

        try:
            results_text = "\n".join([str(r) for r in agent_results])
            prompt = f"""Consolidate these agent results for chain {chain_id}:
{results_text[:2000]}...

Create a final summary and check for consistency."""

            response = await gemini_access.process_request(
                prompt,
                research=False,
                store_findings=True
            )

            result.update({
                "consolidated": True,
                "summary": response.get("response", ""),
                "needs_refinement": False,
                "metadata": response.get("research", {}),
            })
        except Exception as e:
            logger.error("Consolidation failed: %s", e, exc_info=True)
            result.update({
                "consolidated": False,
                "error": str(e),
                "needs_refinement": True,
            })
        return result

    async def assess_quality(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide a quick quality score for a chain output with minimal heuristics.

        Uses an explicit numeric metric when available; otherwise falls back to a
        length-based proxy to avoid accepting empty or trivial responses.
        """
        try:
            quality_metric = result.get("quality_metric")
            if isinstance(quality_metric, (int, float)):
                score = max(0.0, min(1.0, float(quality_metric)))
            else:
                content = result.get("summary") or result.get("response") or ""
                content_len = len(str(content))
                score = min(1.0, content_len / 500) if content_len > 0 else 0.0
        except Exception as e:  # noqa: BLE001
            logger.warning("Quality assessment failed: %s", e, exc_info=True)
            score = 0.0
        
        issues: List[str] = []
        if score <= 0.5:
            issues.append("Content too short or missing quality metric")

        return {
            "quality_score": score,
            "complete": score > 0.5,
            "issues": issues,
        }


def create_agent() -> GeminiLeadAgent:
    """Create agent from command line arguments"""
    base = create_agent_from_args()
    return GeminiLeadAgent(base.config)


async def main():
    agent = create_agent()
    await agent.start()


if __name__ == "__main__":
    asyncio.run(main())
