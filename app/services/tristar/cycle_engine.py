"""
TriStar Cycle Engine v2.80 - Lead → Mesh → Lead Orchestration

Executes a single chain cycle:
1. Lead LLM (Gemini) analyzes the prompt and creates an agent plan
2. Mesh agents execute their assigned tasks in parallel
3. Lead LLM consolidates results and decides next action

This is the core orchestration layer for multi-LLM cooperation.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import json
import logging
import re

logger = logging.getLogger("ailinux.tristar.cycle_engine")


@dataclass
class AgentTask:
    """A task assigned to an agent"""
    task_id: str
    agent: str
    task_type: str
    description: str
    prompt: str
    priority: int = 1
    depends_on: List[str] = field(default_factory=list)
    timeout: int = 120


@dataclass
class AgentPlan:
    """Plan created by lead LLM"""
    analysis: str
    reasoning: str
    tasks: List[AgentTask]
    expected_output: str
    estimated_cycles: int = 1


@dataclass
class CycleResult:
    """Result of a single cycle execution"""
    cycle_number: int
    lead_analysis: str
    agent_plan: Optional[Dict[str, Any]] = None
    agent_tasks: List[Dict[str, Any]] = field(default_factory=list)
    agent_results: Dict[str, Any] = field(default_factory=dict)
    consolidation: Optional[str] = None
    next_action: str = "continue"  # "continue" | "done" | "error"
    tokens_used: int = 0
    execution_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)


class CycleEngine:
    """
    Executes single chain cycles with Lead → Mesh → Lead pattern.

    The Lead LLM (default: Gemini) acts as coordinator:
    1. Analyzes the task
    2. Creates an agent plan with task assignments
    3. Delegates tasks to mesh agents
    4. Consolidates results
    5. Decides if chain should continue or finish
    """

    def __init__(
        self,
        default_lead: str = "gemini",
        default_timeout: int = 120,
        max_parallel_tasks: int = 8,
    ):
        self.default_lead = default_lead
        self.default_timeout = default_timeout
        self.max_parallel_tasks = max_parallel_tasks

    async def execute_cycle(
        self,
        prompt: str,
        autoprompt: Any,  # AutoPromptProfile
        project_id: str,
        cycle_number: int,
        aggressive: bool = False,
        trace_id: Optional[str] = None,
    ) -> CycleResult:
        """
        Execute a single chain cycle.

        Args:
            prompt: Current context/prompt for this cycle
            autoprompt: AutoPrompt profile with system config
            project_id: Project ID for context
            cycle_number: Current cycle number
            aggressive: Enable aggressive parallel execution
            trace_id: Trace ID for audit logging

        Returns:
            CycleResult with all cycle data
        """
        from ..triforce.llm_mesh import llm_call, llm_broadcast, llm_delegate

        start_time = time.time()
        result = CycleResult(
            cycle_number=cycle_number,
            lead_analysis="",
        )

        try:
            # Step 1: Lead analysis and planning
            lead_model = autoprompt.lead_model or self.default_lead
            plan_prompt = self._build_planning_prompt(prompt, autoprompt, cycle_number)

            logger.info(f"Cycle {cycle_number}: Lead ({lead_model}) analyzing task")

            plan_response = await llm_call(
                target=lead_model,
                prompt=plan_prompt,
                caller_llm="tristar_kernel",
                trace_id=trace_id,
                timeout=self.default_timeout,
            )

            if not plan_response.get("success"):
                result.errors.append(f"Lead analysis failed: {plan_response.get('error')}")
                result.next_action = "error"
                return result

            # Parse the plan
            lead_output = plan_response.get("response", "")
            result.lead_analysis = lead_output
            result.tokens_used += self._estimate_tokens(lead_output)

            # Extract agent plan from response
            agent_plan = self._parse_agent_plan(lead_output)
            result.agent_plan = agent_plan

            if not agent_plan.get("tasks"):
                # No tasks to delegate, lead handled it directly
                result.consolidation = lead_output
                if "[CHAIN_DONE]" in lead_output:
                    result.next_action = "done"
                return result

            # Step 2: Execute agent tasks
            logger.info(f"Cycle {cycle_number}: Delegating {len(agent_plan['tasks'])} tasks to mesh agents")

            tasks = agent_plan["tasks"]
            result.agent_tasks = tasks

            # Execute tasks (parallel or sequential based on dependencies)
            max_parallel = autoprompt.parallel_agents if aggressive else min(4, len(tasks))
            agent_results = await self._execute_agent_tasks(
                tasks=tasks,
                max_parallel=max_parallel,
                trace_id=trace_id,
            )

            result.agent_results = agent_results
            result.tokens_used += sum(
                self._estimate_tokens(str(r.get("response", "")))
                for r in agent_results.values()
            )

            # Step 3: Lead consolidation
            logger.info(f"Cycle {cycle_number}: Lead consolidating results")

            consolidation_prompt = self._build_consolidation_prompt(
                original_prompt=prompt,
                agent_plan=agent_plan,
                agent_results=agent_results,
                cycle_number=cycle_number,
            )

            consolidation_response = await llm_call(
                target=lead_model,
                prompt=consolidation_prompt,
                caller_llm="tristar_kernel",
                trace_id=trace_id,
                timeout=self.default_timeout,
            )

            if consolidation_response.get("success"):
                result.consolidation = consolidation_response.get("response", "")
                result.tokens_used += self._estimate_tokens(result.consolidation)

                # Determine next action
                if "[CHAIN_DONE]" in result.consolidation:
                    result.next_action = "done"
                elif "[CHAIN_CONTINUE]" in result.consolidation:
                    result.next_action = "continue"
                elif "[CHAIN_ERROR]" in result.consolidation:
                    result.next_action = "error"
                else:
                    # Default: continue if cycle < max
                    result.next_action = "continue"
            else:
                result.errors.append(f"Consolidation failed: {consolidation_response.get('error')}")
                result.next_action = "error"

        except Exception as e:
            logger.error(f"Cycle {cycle_number} execution error: {e}")
            result.errors.append(str(e))
            result.next_action = "error"

        result.execution_time_ms = (time.time() - start_time) * 1000
        return result

    def _build_planning_prompt(
        self,
        prompt: str,
        autoprompt: Any,
        cycle_number: int,
    ) -> str:
        """Build the planning prompt for lead LLM"""
        return f"""{autoprompt.system_prompt}

CYCLE: {cycle_number}

{autoprompt.task_prefix}{prompt}{autoprompt.task_suffix}

ANWEISUNGEN FÜR DIESE PHASE:

1. Analysiere die Aufgabe gründlich
2. Wenn du die Aufgabe selbst lösen kannst, tue es direkt
3. Wenn du Spezialisten brauchst, erstelle einen AGENT_PLAN

AGENT_PLAN FORMAT:
```agent_plan
{{
  "analysis": "Kurze Analyse der Aufgabe",
  "reasoning": "Warum diese Agenten gewählt wurden",
  "tasks": [
    {{
      "task_id": "task_1",
      "agent": "claude|deepseek|qwen|mistral|cogito|nova|kimi",
      "task_type": "coding|research|review|documentation",
      "description": "Kurze Beschreibung",
      "prompt": "Detaillierter Prompt für den Agenten",
      "priority": 1
    }}
  ],
  "expected_output": "Beschreibung des erwarteten Ergebnisses"
}}
```

Wenn die Aufgabe abgeschlossen ist, antworte mit [CHAIN_DONE] am Ende.
Wenn du weitermachen musst, antworte mit [CHAIN_CONTINUE] am Ende."""

    def _build_consolidation_prompt(
        self,
        original_prompt: str,
        agent_plan: Dict[str, Any],
        agent_results: Dict[str, Any],
        cycle_number: int,
    ) -> str:
        """Build the consolidation prompt for lead LLM"""
        results_text = ""
        for task_id, result in agent_results.items():
            agent = result.get("agent", "unknown")
            response = result.get("response", "No response")
            success = "✓" if result.get("success") else "✗"
            results_text += f"\n### {task_id} ({agent}) [{success}]\n{response}\n"

        return f"""KONSOLIDIERUNG - CYCLE {cycle_number}

URSPRÜNGLICHE AUFGABE:
{original_prompt}

AGENT-PLAN:
{json.dumps(agent_plan, indent=2, ensure_ascii=False)}

AGENT-ERGEBNISSE:
{results_text}

ANWEISUNGEN:
1. Analysiere alle Agent-Ergebnisse
2. Fasse die Erkenntnisse zusammen
3. Identifiziere offene Punkte
4. Erstelle eine kohärente Antwort

AUSGABE:
- Beginne mit einer Zusammenfassung
- Füge Details und Ergebnisse hinzu
- Ende mit [CHAIN_DONE] wenn die Aufgabe abgeschlossen ist
- Ende mit [CHAIN_CONTINUE] wenn noch weitere Arbeit nötig ist
- Ende mit [CHAIN_ERROR] wenn kritische Fehler aufgetreten sind"""

    def _parse_agent_plan(self, response: str) -> Dict[str, Any]:
        """Parse agent plan from lead LLM response"""
        # Try to extract JSON from agent_plan block
        pattern = r"```agent_plan\s*([\s\S]*?)\s*```"
        match = re.search(pattern, response)

        if match:
            try:
                plan = json.loads(match.group(1))
                return plan
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse agent plan JSON: {e}")

        # Try to find any JSON object in the response
        json_pattern = r"\{[\s\S]*\"tasks\"[\s\S]*\}"
        json_match = re.search(json_pattern, response)

        if json_match:
            try:
                plan = json.loads(json_match.group(0))
                return plan
            except json.JSONDecodeError:
                pass

        # No plan found, return empty
        return {"analysis": response, "tasks": []}

    async def _execute_agent_tasks(
        self,
        tasks: List[Dict[str, Any]],
        max_parallel: int,
        trace_id: Optional[str],
    ) -> Dict[str, Any]:
        """Execute agent tasks with parallel/sequential handling"""
        from ..triforce.llm_mesh import llm_call, llm_delegate

        results = {}

        # Group tasks by dependency
        no_deps = [t for t in tasks if not t.get("depends_on")]
        with_deps = [t for t in tasks if t.get("depends_on")]

        # Execute tasks without dependencies in parallel
        if no_deps:
            async def execute_task(task: Dict[str, Any]) -> tuple:
                task_id = task.get("task_id", "unknown")
                agent = task.get("agent", "claude")
                task_type = task.get("task_type", "general")
                prompt = task.get("prompt", "")

                try:
                    result = await llm_delegate(
                        target=agent,
                        task_type=task_type,
                        prompt=prompt,
                        caller_llm="tristar_kernel",
                        trace_id=trace_id,
                    )
                    return task_id, {
                        "agent": agent,
                        "success": result.get("success", False),
                        "response": result.get("response", ""),
                        "error": result.get("error"),
                    }
                except Exception as e:
                    return task_id, {
                        "agent": agent,
                        "success": False,
                        "response": "",
                        "error": str(e),
                    }

            # Execute in batches
            for i in range(0, len(no_deps), max_parallel):
                batch = no_deps[i:i + max_parallel]
                batch_results = await asyncio.gather(
                    *[execute_task(t) for t in batch],
                    return_exceptions=True
                )

                for item in batch_results:
                    if isinstance(item, Exception):
                        logger.error(f"Task execution error: {item}")
                    else:
                        task_id, result = item
                        results[task_id] = result

        # Execute tasks with dependencies sequentially
        for task in with_deps:
            task_id = task.get("task_id", "unknown")

            # Check if dependencies are satisfied
            deps_satisfied = all(
                dep in results and results[dep].get("success")
                for dep in task.get("depends_on", [])
            )

            if not deps_satisfied:
                results[task_id] = {
                    "agent": task.get("agent", "unknown"),
                    "success": False,
                    "response": "",
                    "error": "Dependencies not satisfied",
                }
                continue

            # Build context from dependencies
            dep_context = "\n".join([
                f"Result from {dep}:\n{results[dep].get('response', '')}"
                for dep in task.get("depends_on", [])
            ])

            enhanced_prompt = f"{task.get('prompt', '')}\n\nCONTEXT FROM PREVIOUS TASKS:\n{dep_context}"

            try:
                result = await llm_delegate(
                    target=task.get("agent", "claude"),
                    task_type=task.get("task_type", "general"),
                    prompt=enhanced_prompt,
                    caller_llm="tristar_kernel",
                    trace_id=trace_id,
                )
                results[task_id] = {
                    "agent": task.get("agent", "unknown"),
                    "success": result.get("success", False),
                    "response": result.get("response", ""),
                    "error": result.get("error"),
                }
            except Exception as e:
                results[task_id] = {
                    "agent": task.get("agent", "unknown"),
                    "success": False,
                    "response": "",
                    "error": str(e),
                }

        return results

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token)"""
        return len(text) // 4


# Singleton instance
cycle_engine = CycleEngine()
