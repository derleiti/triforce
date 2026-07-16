import logging
from typing import Dict, Any, Optional
from app.config import get_settings
# from app.services.model_registry import ModelRegistry # Annahme: ModelRegistry existiert

logger = logging.getLogger(__name__)

# Dummy ModelRegistry für das Beispiel
class ModelRegistry:
    def get_model_info(self, provider_id: str) -> Optional[Dict[str, Any]]:
        s = get_settings()
        if provider_id == s.LLM_DEFAULT:
            return {"model_id": s.GPT_OSS_MODEL_ID, "api_base": s.GPT_OSS_API_BASE, "api_key": s.GPT_OSS_API_KEY}
        elif provider_id == s.LLM_HEAVY:
            return {"model_id": s.DEEPSEEK_MODEL_ID, "api_base": s.DEEPSEEK_API_BASE, "api_key": s.DEEPSEEK_API_KEY}
        elif provider_id == s.OPENROUTER_MODEL_ID:
            return {"model_id": s.OPENROUTER_MODEL_ID, "api_base": s.OPENROUTER_API_BASE, "api_key": s.OPENROUTER_API_KEY}
        return None

class LLMRouter:
    def __init__(self, model_registry: ModelRegistry):
        self.model_registry = model_registry
        s = get_settings() # Get settings inside __init__
        self.policy_rules = [
            {
                "when": lambda task, messages: task in ['arch', 'longform', 'security_review'] or self._is_long_text(messages),
                "use": s.LLM_HEAVY,
                "max_tokens": 3500,
                "timeout_ms": s.DEEPSEEK_TIMEOUT_MS,
                "provider_base": s.DEEPSEEK_API_BASE,
                "api_key": s.DEEPSEEK_API_KEY,
                "model_id": s.DEEPSEEK_MODEL_ID,
                "fallback": s.LLM_DEFAULT # Fallback to default if heavy fails
            },
            {
                "when": lambda task, messages: task in ['chat', 'small_fix', 'summarize'],
                "use": s.LLM_DEFAULT,
                "max_tokens": 1200,
                "timeout_ms": s.GPT_OSS_TIMEOUT_MS,
                "provider_base": s.GPT_OSS_API_BASE,
                "api_key": s.GPT_OSS_API_KEY,
                "model_id": s.GPT_OSS_MODEL_ID,
                "fallback": s.OPENROUTER_MODEL_ID # Fallback to OpenRouter if default fails
            },
            {
                "when": lambda task, messages: "latency_critical" in task, # Annahme: task kann auch Tags enthalten
                "use": s.OPENROUTER_MODEL_ID,
                "max_tokens": 900,
                "timeout_ms": s.OPENROUTER_TIMEOUT_MS,
                "provider_base": s.OPENROUTER_API_BASE,
                "api_key": s.OPENROUTER_API_KEY,
                "model_id": s.OPENROUTER_MODEL_ID,
                "fallback": s.LLM_DEFAULT
            }
            # Weitere Regeln hier hinzufügen, z.B. für ZukiJourney oder Ollama
        ]

    def _is_long_text(self, messages: list[Dict[str, Any]]) -> bool:
        # Einfache Heuristik: Zähle die Gesamtzeichen in den Nachrichten
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars > 1000 # Beispiel: Als "Langtext" gilt alles über 1000 Zeichen

    async def route(self, task: str, messages: list[Dict[str, Any]], user_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Routes a chat request to the appropriate LLM based on task type and message content.
        """
        if user_options is None:
            user_options = {}

        chosen_rule = None
        s = get_settings()
        for rule in self.policy_rules:
            if rule["when"](task, messages):
                chosen_rule = rule
                break

        if not chosen_rule:
            # Fallback to default if no specific rule matches
            logger.warning(f"No specific LLM routing rule matched for task '{task}'. Falling back to default.")
            chosen_rule = {
                "use": s.LLM_DEFAULT,
                "max_tokens": 1200,
                "timeout_ms": s.GPT_OSS_TIMEOUT_MS,
                "provider_base": s.GPT_OSS_API_BASE,
                "api_key": s.GPT_OSS_API_KEY,
                "model_id": s.GPT_OSS_MODEL_ID,
                "fallback": None
            }

        # Merge user options with chosen rule defaults
        final_options = {
            "temperature": 0.3,
            "top_p": 0.9,
            "max_tokens": chosen_rule.get("max_tokens"),
            "timeout_ms": chosen_rule.get("timeout_ms"),
            **user_options
        }

        provider_id = chosen_rule["use"]
        model_info = self.model_registry.get_model_info(provider_id) # Annahme: ModelRegistry kann Infos liefern

        if not model_info:
            logger.error(f"Model info not found for provider_id: {provider_id}. Falling back to default.")
            provider_id = s.LLM_DEFAULT
            model_info = self.model_registry.get_model_info(provider_id)
            if not model_info:
                raise ValueError(f"Default LLM '{s.LLM_DEFAULT}' not found in registry.")

        return {
            "provider_id": provider_id,
            "model_id": chosen_rule.get("model_id") or model_info.get("model_id"), # Use rule's specific model_id if present
            "api_base": chosen_rule.get("provider_base") or model_info.get("api_base"),
            "api_key": chosen_rule.get("api_key") or model_info.get("api_key"),
            "options": final_options,
            "fallback_provider_id": chosen_rule.get("fallback")
        }
