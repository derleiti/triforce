"""
Context Management for MCP

Provides conversation context management, prompt templates, and
multi-turn conversation handling for Claude Code integration.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from collections import OrderedDict


@dataclass
class Message:
    """A single message in a conversation."""
    role: str  # system, user, assistant
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class ConversationContext:
    """Manages context for a conversation session."""

    session_id: str
    messages: List[Message] = field(default_factory=list)
    system_prompt: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    max_messages: int = 50
    token_estimate: int = 0

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> Message:
        """Add a message to the conversation."""
        msg = Message(role=role, content=content, metadata=metadata or {})
        self.messages.append(msg)
        self.last_active = time.time()

        # Estimate tokens (rough: 1 token ≈ 4 chars)
        self.token_estimate += len(content) // 4

        # Trim old messages if needed
        while len(self.messages) > self.max_messages:
            removed = self.messages.pop(0)
            self.token_estimate -= len(removed.content) // 4

        return msg

    def add_user_message(self, content: str, metadata: Optional[Dict] = None) -> Message:
        return self.add_message("user", content, metadata)

    def add_assistant_message(self, content: str, metadata: Optional[Dict] = None) -> Message:
        return self.add_message("assistant", content, metadata)

    def set_system_prompt(self, prompt: str) -> None:
        """Set or update the system prompt."""
        self.system_prompt = prompt

    def get_messages_for_api(self) -> List[Dict[str, str]]:
        """Get messages formatted for API call."""
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        for msg in self.messages:
            messages.append({"role": msg.role, "content": msg.content})
        return messages

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the conversation."""
        return {
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "token_estimate": self.token_estimate,
            "created_at": datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat(),
            "last_active": datetime.fromtimestamp(self.last_active, tz=timezone.utc).isoformat(),
            "has_system_prompt": self.system_prompt is not None
        }

    def clear(self) -> None:
        """Clear all messages but keep system prompt."""
        self.messages = []
        self.token_estimate = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "system_prompt": self.system_prompt,
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "token_estimate": self.token_estimate
        }


class ContextManager:
    """
    Manages multiple conversation contexts with LRU eviction.
    Provides context persistence and retrieval for Claude Code sessions.
    """

    def __init__(self, max_contexts: int = 100, context_ttl: int = 3600):
        """
        Args:
            max_contexts: Maximum number of contexts to keep in memory
            context_ttl: Time-to-live for contexts in seconds (default 1 hour)
        """
        self.contexts: OrderedDict[str, ConversationContext] = OrderedDict()
        self.max_contexts = max_contexts
        self.context_ttl = context_ttl

    def create_context(
        self,
        session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> ConversationContext:
        """Create a new conversation context."""
        if session_id is None:
            session_id = self._generate_session_id()

        context = ConversationContext(
            session_id=session_id,
            system_prompt=system_prompt,
            metadata=metadata or {}
        )

        self._add_context(context)
        return context

    def get_context(self, session_id: str) -> Optional[ConversationContext]:
        """Get an existing context by session ID."""
        if session_id in self.contexts:
            context = self.contexts[session_id]
            # Check TTL
            if time.time() - context.last_active > self.context_ttl:
                del self.contexts[session_id]
                return None
            # Move to end (LRU)
            self.contexts.move_to_end(session_id)
            return context
        return None

    def get_or_create_context(
        self,
        session_id: str,
        system_prompt: Optional[str] = None
    ) -> ConversationContext:
        """Get existing context or create new one."""
        context = self.get_context(session_id)
        if context:
            return context
        return self.create_context(session_id, system_prompt)

    def delete_context(self, session_id: str) -> bool:
        """Delete a context."""
        if session_id in self.contexts:
            del self.contexts[session_id]
            return True
        return False

    def list_contexts(self) -> List[Dict[str, Any]]:
        """List all active contexts."""
        self._cleanup_expired()
        return [ctx.get_summary() for ctx in self.contexts.values()]

    def _add_context(self, context: ConversationContext) -> None:
        """Add context with LRU eviction."""
        if len(self.contexts) >= self.max_contexts:
            # Remove oldest
            self.contexts.popitem(last=False)
        self.contexts[context.session_id] = context

    def _cleanup_expired(self) -> None:
        """Remove expired contexts."""
        now = time.time()
        expired = [
            sid for sid, ctx in self.contexts.items()
            if now - ctx.last_active > self.context_ttl
        ]
        for sid in expired:
            del self.contexts[sid]

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        data = f"{time.time()}-{id(self)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


# =============================================================================
# Prompt Templates
# =============================================================================

PROMPT_TEMPLATES = {
    "code_review": """You are an expert code reviewer. Analyze the following code for:
- Code quality and best practices
- Potential bugs and edge cases
- Security vulnerabilities
- Performance issues
- Maintainability and readability

Provide specific, actionable feedback with line numbers where applicable.

Code to review:
{code}""",

    "architecture_design": """You are a software architect designing a system. Consider:
- Scalability requirements
- Security implications
- Maintainability and testability
- Technology stack decisions
- Trade-offs and alternatives

Task: {task}

Current context: {context}""",

    "debugging": """You are a debugging expert. Analyze the following error and code:

Error: {error}

Code context:
{code}

Provide:
1. Root cause analysis
2. Step-by-step fix
3. Prevention strategies""",

    "documentation": """Generate comprehensive documentation for the following code.
Include:
- Purpose and functionality
- Parameters and return values
- Usage examples
- Edge cases and limitations

Code:
{code}""",

    "security_audit": """Perform a security audit of the following code. Check for:
- OWASP Top 10 vulnerabilities
- Input validation issues
- Authentication/authorization flaws
- Data exposure risks
- Injection vulnerabilities

Code:
{code}""",

    "german_content": """Du bist ein Experte für deutsche Inhalte. Schreibe den folgenden Text auf Deutsch:

Thema: {topic}

Anforderungen:
- Professioneller, klarer Stil
- Korrekte Grammatik und Rechtschreibung
- Angemessener Ton für die Zielgruppe

{additional_instructions}""",

    "summarization": """Summarize the following content concisely:

{content}

Provide:
1. Main points (bullet list)
2. Key takeaways
3. Brief conclusion""",

    "crawler_analysis": """Analyze the crawled content and extract:
1. Main topics and themes
2. Key information and facts
3. Relevant links and references
4. Content quality assessment

Crawled content:
{content}

Keywords of interest: {keywords}""",

    "wordpress_post": """Create a WordPress blog post based on the following information:

Topic: {topic}
Keywords: {keywords}
Tone: {tone}

Include:
- Engaging title
- SEO-optimized introduction
- Structured content with headers
- Call to action
- Meta description suggestion"""
}


class PromptLibrary:
    """
    Manages prompt templates with variable substitution.
    Allows Claude Code to use standardized prompts for common tasks.
    """

    def __init__(self):
        self.templates = PROMPT_TEMPLATES.copy()
        self.custom_templates: Dict[str, str] = {}

    def get_template(self, name: str) -> Optional[str]:
        """Get a template by name."""
        return self.custom_templates.get(name) or self.templates.get(name)

    def list_templates(self) -> List[str]:
        """List all available template names."""
        return list(set(self.templates.keys()) | set(self.custom_templates.keys()))

    def render(self, name: str, **variables) -> str:
        """
        Render a template with variables.

        Args:
            name: Template name
            **variables: Variables to substitute

        Returns:
            Rendered prompt string

        Raises:
            ValueError: If template not found
        """
        template = self.get_template(name)
        if not template:
            raise ValueError(f"Template '{name}' not found. Available: {self.list_templates()}")

        # Simple variable substitution
        result = template
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            result = result.replace(placeholder, str(value) if value else "")

        return result

    def add_template(self, name: str, template: str) -> None:
        """Add or update a custom template."""
        self.custom_templates[name] = template

    def remove_template(self, name: str) -> bool:
        """Remove a custom template."""
        if name in self.custom_templates:
            del self.custom_templates[name]
            return True
        return False

    def get_template_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a template including its variables."""
        template = self.get_template(name)
        if not template:
            return None

        # Extract variables
        import re
        variables = re.findall(r'\{(\w+)\}', template)

        return {
            "name": name,
            "is_builtin": name in self.templates,
            "variables": list(set(variables)),
            "preview": template[:200] + "..." if len(template) > 200 else template
        }


# =============================================================================
# Workflow Orchestration
# =============================================================================

@dataclass
class WorkflowStep:
    """A step in a workflow."""
    name: str
    description: str
    specialist_id: Optional[str] = None
    prompt_template: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    output_key: str = ""
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class Workflow:
    """A multi-step workflow."""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending, running, completed, failed

    def get_ready_steps(self) -> List[WorkflowStep]:
        """Get steps that are ready to execute."""
        completed_steps = {s.name for s in self.steps if s.status == "completed"}
        ready = []
        for step in self.steps:
            if step.status != "pending":
                continue
            if all(dep in completed_steps for dep in step.depends_on):
                ready.append(step)
        return ready

    def mark_step_complete(self, step_name: str, result: str) -> None:
        """Mark a step as completed."""
        for step in self.steps:
            if step.name == step_name:
                step.status = "completed"
                step.result = result
                if step.output_key:
                    self.context[step.output_key] = result
                break

    def mark_step_failed(self, step_name: str, error: str) -> None:
        """Mark a step as failed."""
        for step in self.steps:
            if step.name == step_name:
                step.status = "failed"
                step.error = error
                self.status = "failed"
                break

    def is_complete(self) -> bool:
        """Check if workflow is complete."""
        return all(s.status == "completed" for s in self.steps)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [
                {
                    "name": s.name,
                    "description": s.description,
                    "specialist_id": s.specialist_id,
                    "depends_on": s.depends_on,
                    "status": s.status,
                    "result_preview": s.result[:100] + "..." if s.result and len(s.result) > 100 else s.result,
                    "error": s.error
                }
                for s in self.steps
            ],
            "status": self.status,
            "created_at": datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat()
        }


# =============================================================================
# Predefined Workflows
# =============================================================================

WORKFLOW_TEMPLATES = {
    "content_pipeline": {
        "name": "Content Creation Pipeline",
        "description": "Crawl website, analyze content, generate blog post",
        "steps": [
            {
                "name": "crawl",
                "description": "Crawl the target website",
                "specialist_id": None,  # Uses crawler, not LLM
                "output_key": "crawled_content"
            },
            {
                "name": "analyze",
                "description": "Analyze crawled content",
                "specialist_id": "gemini-flash",
                "prompt_template": "crawler_analysis",
                "depends_on": ["crawl"],
                "output_key": "analysis"
            },
            {
                "name": "write",
                "description": "Generate WordPress post",
                "specialist_id": "claude-sonnet",
                "prompt_template": "wordpress_post",
                "depends_on": ["analyze"],
                "output_key": "post_content"
            },
            {
                "name": "publish",
                "description": "Publish to WordPress",
                "specialist_id": None,  # Uses API, not LLM
                "depends_on": ["write"]
            }
        ]
    },

    "code_quality": {
        "name": "Code Quality Pipeline",
        "description": "Review code, suggest improvements, generate documentation",
        "steps": [
            {
                "name": "security_check",
                "description": "Security vulnerability scan",
                "specialist_id": "claude-opus",
                "prompt_template": "security_audit",
                "output_key": "security_report"
            },
            {
                "name": "code_review",
                "description": "Code quality review",
                "specialist_id": "claude-sonnet",
                "prompt_template": "code_review",
                "output_key": "review_report"
            },
            {
                "name": "documentation",
                "description": "Generate documentation",
                "specialist_id": "claude-haiku",
                "prompt_template": "documentation",
                "depends_on": ["code_review"],
                "output_key": "documentation"
            }
        ]
    },

    "german_localization": {
        "name": "German Localization Pipeline",
        "description": "Translate and localize content for German audience",
        "steps": [
            {
                "name": "translate",
                "description": "Translate content to German",
                "specialist_id": "gpt-oss",
                "prompt_template": "german_content",
                "output_key": "german_content"
            },
            {
                "name": "review",
                "description": "Review German translation",
                "specialist_id": "claude-sonnet",
                "depends_on": ["translate"],
                "output_key": "reviewed_content"
            }
        ]
    }
}


class WorkflowManager:
    """Manages workflow execution and state."""

    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self.templates = WORKFLOW_TEMPLATES

    def create_workflow(
        self,
        template_name: str,
        workflow_id: Optional[str] = None,
        initial_context: Optional[Dict] = None
    ) -> Workflow:
        """Create a workflow from a template."""
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")

        template = self.templates[template_name]
        workflow_id = workflow_id or hashlib.sha256(
            f"{time.time()}-{template_name}".encode()
        ).hexdigest()[:12]

        steps = []
        for step_def in template["steps"]:
            steps.append(WorkflowStep(
                name=step_def["name"],
                description=step_def["description"],
                specialist_id=step_def.get("specialist_id"),
                prompt_template=step_def.get("prompt_template"),
                depends_on=step_def.get("depends_on", []),
                output_key=step_def.get("output_key", "")
            ))

        workflow = Workflow(
            id=workflow_id,
            name=template["name"],
            description=template["description"],
            steps=steps,
            context=initial_context or {}
        )

        self.workflows[workflow_id] = workflow
        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID."""
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows."""
        return [w.to_dict() for w in self.workflows.values()]

    def list_templates(self) -> List[Dict[str, Any]]:
        """List available workflow templates."""
        return [
            {
                "name": name,
                "display_name": template["name"],
                "description": template["description"],
                "step_count": len(template["steps"])
            }
            for name, template in self.templates.items()
        ]


# Global instances
context_manager = ContextManager()
prompt_library = PromptLibrary()
workflow_manager = WorkflowManager()
