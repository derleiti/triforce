"""
Hugging Face Inference API Service
===================================

Integration für HF Inference API (Free Tier) mit Support für:
- Text Generation (LLMs wie Llama, Mistral, Qwen)
- Embeddings (sentence-transformers)
- Text-to-Image (FLUX, Stable Diffusion)
- Chat Completions (OpenAI-kompatibel)

Version: 1.0
Erstellt für TriForce v2.80

Erkenntnisse aus KI-Befragung:
- Async mit Retry-Logic
- Circuit Breaker für Rate Limits
- Memory-Integration für Ergebnisse
- Graceful Degradation bei API-Ausfall
"""

import asyncio
import base64
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import httpx

from ..config import get_settings

logger = logging.getLogger("ailinux.huggingface")
settings = get_settings()


class HuggingFaceInferenceError(Exception):
    """Custom exception for HF Inference errors."""
    pass


class HuggingFaceInference:
    """
    Hugging Face Inference API Client.

    Unterstützt Free Tier mit Rate Limiting und Retry-Logic.
    """

    # Empfohlene Modelle für verschiedene Tasks
    RECOMMENDED_MODELS = {
        "text_generation": [
            "meta-llama/Llama-3.2-3B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "Qwen/Qwen2.5-7B-Instruct",
            "microsoft/Phi-3-mini-4k-instruct",
        ],
        "chat": [
            "meta-llama/Llama-3.2-3B-Instruct",
            "HuggingFaceH4/zephyr-7b-beta",
        ],
        "embeddings": [
            "sentence-transformers/all-MiniLM-L6-v2",
            "BAAI/bge-small-en-v1.5",
            "intfloat/multilingual-e5-small",
        ],
        "text_to_image": [
            "black-forest-labs/FLUX.1-schnell",
            "stabilityai/stable-diffusion-xl-base-1.0",
            "runwayml/stable-diffusion-v1-5",
        ],
        "summarization": [
            "facebook/bart-large-cnn",
            "google/pegasus-xsum",
        ],
        "translation": [
            "Helsinki-NLP/opus-mt-de-en",
            "Helsinki-NLP/opus-mt-en-de",
        ],
    }

    def __init__(self):
        self.base_url = str(getattr(settings, 'huggingface_inference_url', 'https://router.huggingface.co/hf-inference')).rstrip("/")
        self.api_key = getattr(settings, 'huggingface_api_key', None)
        self.timeout = getattr(settings, 'huggingface_timeout', 120)
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_remaining: int = 100
        self._rate_limit_reset: Optional[datetime] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-init async HTTP client."""
        if not self._client or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _update_rate_limits(self, response: httpx.Response):
        """Update rate limit info from response headers."""
        if "x-ratelimit-remaining" in response.headers:
            try:
                self._rate_limit_remaining = int(response.headers["x-ratelimit-remaining"])
            except ValueError:
                pass
        if "x-ratelimit-reset" in response.headers:
            try:
                reset_ts = int(response.headers["x-ratelimit-reset"])
                self._rate_limit_reset = datetime.fromtimestamp(reset_ts, tz=timezone.utc)
            except ValueError:
                pass

    async def _request(
        self,
        model: str,
        payload: Dict[str, Any],
        endpoint_suffix: str = "",
        retry_count: int = 3,
        retry_delay: float = 2.0,
    ) -> Union[Dict, bytes]:
        """
        Make request to HF Inference API with retry logic.

        Args:
            model: HF model ID
            payload: Request payload
            endpoint_suffix: Optional endpoint suffix (e.g., "/v1/chat/completions")
            retry_count: Number of retries
            retry_delay: Delay between retries in seconds

        Returns:
            JSON response or raw bytes (for images)
        """
        url = f"{self.base_url}/models/{model}{endpoint_suffix}"

        last_error = None
        for attempt in range(retry_count):
            try:
                response = await self.client.post(url, json=payload)
                self._update_rate_limits(response)

                # Handle rate limiting
                if response.status_code == 429:
                    wait_time = float(response.headers.get("retry-after", retry_delay * (attempt + 1)))
                    logger.warning(f"Rate limited, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue

                # Handle model loading
                if response.status_code == 503:
                    try:
                        data = response.json()
                        if "estimated_time" in data:
                            wait_time = min(data["estimated_time"], 60)
                            logger.info(f"Model loading, waiting {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue
                    except Exception:
                        pass

                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("content-type", "")
                if "image" in content_type:
                    return response.content

                return response.json()

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(f"HTTP error (attempt {attempt + 1}): {e}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
            except Exception as e:
                last_error = e
                logger.error(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(retry_delay)

        raise HuggingFaceInferenceError(f"Request failed after {retry_count} attempts: {last_error}")

    # ═══════════════════════════════════════════════════════════════════════
    # TEXT GENERATION
    # ═══════════════════════════════════════════════════════════════════════

    async def text_generation(
        self,
        prompt: str,
        model: str = "meta-llama/Llama-3.2-3B-Instruct",
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.95,
        do_sample: bool = True,
        return_full_text: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate text using a HF model.

        Args:
            prompt: Input prompt
            model: HF model ID
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling
            do_sample: Enable sampling (False = greedy)
            return_full_text: Include prompt in response

        Returns:
            Dict with generated_text and metadata
        """
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "do_sample": do_sample,
                "return_full_text": return_full_text,
                **kwargs,
            },
        }

        result = await self._request(model, payload)

        # Normalize response format
        if isinstance(result, list) and len(result) > 0:
            return {
                "generated_text": result[0].get("generated_text", ""),
                "model": model,
                "usage": {"prompt_tokens": len(prompt.split()), "completion_tokens": max_new_tokens},
            }

        return {"generated_text": str(result), "model": model}

    # ═══════════════════════════════════════════════════════════════════════
    # CHAT COMPLETION (OpenAI-kompatibel)
    # ═══════════════════════════════════════════════════════════════════════

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "meta-llama/Llama-3.2-3B-Instruct",
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Chat completion (OpenAI-compatible endpoint).

        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            model: HF model ID with chat support
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            stream: Enable streaming (not implemented yet)

        Returns:
            OpenAI-compatible response format
        """
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
            **kwargs,
        }

        try:
            result = await self._request(model, payload, endpoint_suffix="/v1/chat/completions")
            return result
        except HuggingFaceInferenceError:
            # Fallback: Try regular text generation with formatted prompt
            prompt = self._format_chat_messages(messages)
            gen_result = await self.text_generation(
                prompt=prompt,
                model=model,
                max_new_tokens=max_tokens,
                temperature=temperature,
            )
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": gen_result.get("generated_text", ""),
                    },
                    "index": 0,
                }],
                "model": model,
                "usage": gen_result.get("usage", {}),
            }

    def _format_chat_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format chat messages as a prompt string."""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                formatted.append(f"System: {content}")
            elif role == "user":
                formatted.append(f"User: {content}")
            elif role == "assistant":
                formatted.append(f"Assistant: {content}")
        formatted.append("Assistant:")
        return "\n".join(formatted)

    # ═══════════════════════════════════════════════════════════════════════
    # EMBEDDINGS
    # ═══════════════════════════════════════════════════════════════════════

    async def embeddings(
        self,
        texts: Union[str, List[str]],
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> Dict[str, Any]:
        """
        Generate embeddings for text(s).

        Args:
            texts: Single text or list of texts
            model: Embedding model ID

        Returns:
            Dict with embeddings list and metadata
        """
        if isinstance(texts, str):
            texts = [texts]

        payload = {"inputs": texts}
        result = await self._request(model, payload)

        # Handle different response formats
        if isinstance(result, list):
            if len(result) > 0 and isinstance(result[0], list):
                # Already nested embeddings
                embeddings = result
            else:
                # Single embedding, wrap it
                embeddings = [result]
        else:
            embeddings = result.get("embeddings", [])

        return {
            "embeddings": embeddings,
            "model": model,
            "dimension": len(embeddings[0]) if embeddings and len(embeddings) > 0 else 0,
            "count": len(embeddings),
        }

    # ═══════════════════════════════════════════════════════════════════════
    # TEXT-TO-IMAGE
    # ═══════════════════════════════════════════════════════════════════════

    async def text_to_image(
        self,
        prompt: str,
        model: str = "black-forest-labs/FLUX.1-schnell",
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 4,
        guidance_scale: float = 0.0,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate image from text prompt.

        Args:
            prompt: Image description
            model: Image generation model
            negative_prompt: What to avoid in image
            width: Image width
            height: Image height
            num_inference_steps: Denoising steps (more = better quality, slower)
            guidance_scale: CFG scale (0 for FLUX.1-schnell)

        Returns:
            Dict with base64 image and metadata
        """
        payload = {
            "inputs": prompt,
            "parameters": {
                "width": width,
                "height": height,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                **kwargs,
            },
        }

        if negative_prompt:
            payload["parameters"]["negative_prompt"] = negative_prompt

        image_bytes = await self._request(model, payload)

        if isinstance(image_bytes, bytes):
            return {
                "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
                "model": model,
                "prompt": prompt,
                "width": width,
                "height": height,
                "format": "png",
            }

        return {"error": "Unexpected response format", "raw": str(image_bytes)}

    # ═══════════════════════════════════════════════════════════════════════
    # SUMMARIZATION
    # ═══════════════════════════════════════════════════════════════════════

    async def summarize(
        self,
        text: str,
        model: str = "facebook/bart-large-cnn",
        max_length: int = 150,
        min_length: int = 30,
    ) -> Dict[str, Any]:
        """Summarize text."""
        payload = {
            "inputs": text,
            "parameters": {
                "max_length": max_length,
                "min_length": min_length,
            },
        }

        result = await self._request(model, payload)

        if isinstance(result, list) and len(result) > 0:
            return {"summary": result[0].get("summary_text", ""), "model": model}

        return {"summary": str(result), "model": model}

    # ═══════════════════════════════════════════════════════════════════════
    # TRANSLATION
    # ═══════════════════════════════════════════════════════════════════════

    async def translate(
        self,
        text: str,
        model: str = "Helsinki-NLP/opus-mt-de-en",
    ) -> Dict[str, Any]:
        """Translate text."""
        payload = {"inputs": text}
        result = await self._request(model, payload)

        if isinstance(result, list) and len(result) > 0:
            return {"translation": result[0].get("translation_text", ""), "model": model}

        return {"translation": str(result), "model": model}

    # ═══════════════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════════

    def get_recommended_model(self, task: str) -> Optional[str]:
        """Get recommended model for a task."""
        models = self.RECOMMENDED_MODELS.get(task, [])
        return models[0] if models else None

    def list_recommended_models(self) -> Dict[str, List[str]]:
        """List all recommended models by task."""
        return self.RECOMMENDED_MODELS.copy()

    @property
    def rate_limit_info(self) -> Dict[str, Any]:
        """Get current rate limit info."""
        return {
            "remaining": self._rate_limit_remaining,
            "reset": self._rate_limit_reset.isoformat() if self._rate_limit_reset else None,
        }


# Singleton Instance
hf_inference = HuggingFaceInference()


# ═══════════════════════════════════════════════════════════════════════════
# MCP TOOL DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

HF_INFERENCE_TOOLS = [
    {
        "name": "hf_generate",
        "description": "Text generation via Hugging Face Inference API (Llama, Mistral, Qwen, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Input prompt"},
                "model": {
                    "type": "string",
                    "default": "meta-llama/Llama-3.2-3B-Instruct",
                    "description": "HF Model ID",
                },
                "max_new_tokens": {"type": "integer", "default": 512},
                "temperature": {"type": "number", "default": 0.7},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "hf_chat",
        "description": "Chat completion via Hugging Face (OpenAI-compatible)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string", "enum": ["system", "user", "assistant"]},
                            "content": {"type": "string"},
                        },
                    },
                    "description": "Chat messages",
                },
                "model": {"type": "string", "default": "meta-llama/Llama-3.2-3B-Instruct"},
                "max_tokens": {"type": "integer", "default": 512},
                "temperature": {"type": "number", "default": 0.7},
            },
            "required": ["messages"],
        },
    },
    {
        "name": "hf_embed",
        "description": "Generate embeddings via Hugging Face (sentence-transformers)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "texts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Texts to embed",
                },
                "model": {
                    "type": "string",
                    "default": "sentence-transformers/all-MiniLM-L6-v2",
                },
            },
            "required": ["texts"],
        },
    },
    {
        "name": "hf_image",
        "description": "Text-to-Image via Hugging Face (FLUX, Stable Diffusion)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Image description"},
                "model": {
                    "type": "string",
                    "default": "black-forest-labs/FLUX.1-schnell",
                },
                "negative_prompt": {"type": "string"},
                "width": {"type": "integer", "default": 1024},
                "height": {"type": "integer", "default": 1024},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "hf_summarize",
        "description": "Summarize text via Hugging Face",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to summarize"},
                "model": {"type": "string", "default": "facebook/bart-large-cnn"},
                "max_length": {"type": "integer", "default": 150},
            },
            "required": ["text"],
        },
    },
    {
        "name": "hf_translate",
        "description": "Translate text via Hugging Face (OPUS-MT)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to translate"},
                "model": {
                    "type": "string",
                    "default": "Helsinki-NLP/opus-mt-de-en",
                    "description": "Translation model (de-en, en-de, etc.)",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "hf_models",
        "description": "List recommended Hugging Face models by task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "enum": ["text_generation", "chat", "embeddings", "text_to_image", "summarization", "translation"],
                    "description": "Task type (optional, list all if not specified)",
                },
            },
        },
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# MCP HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

async def handle_hf_generate(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle hf_generate tool."""
    prompt = args.get("prompt")
    if not prompt:
        raise ValueError("'prompt' is required")

    return await hf_inference.text_generation(
        prompt=prompt,
        model=args.get("model", "meta-llama/Llama-3.2-3B-Instruct"),
        max_new_tokens=args.get("max_new_tokens", 512),
        temperature=args.get("temperature", 0.7),
    )


async def handle_hf_chat(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle hf_chat tool."""
    messages = args.get("messages")
    if not messages:
        raise ValueError("'messages' is required")

    return await hf_inference.chat_completion(
        messages=messages,
        model=args.get("model", "meta-llama/Llama-3.2-3B-Instruct"),
        max_tokens=args.get("max_tokens", 512),
        temperature=args.get("temperature", 0.7),
    )


async def handle_hf_embed(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle hf_embed tool."""
    texts = args.get("texts")
    if not texts:
        raise ValueError("'texts' is required")

    return await hf_inference.embeddings(
        texts=texts,
        model=args.get("model", "sentence-transformers/all-MiniLM-L6-v2"),
    )


async def handle_hf_image(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle hf_image tool."""
    prompt = args.get("prompt")
    if not prompt:
        raise ValueError("'prompt' is required")

    return await hf_inference.text_to_image(
        prompt=prompt,
        model=args.get("model", "black-forest-labs/FLUX.1-schnell"),
        negative_prompt=args.get("negative_prompt"),
        width=args.get("width", 1024),
        height=args.get("height", 1024),
    )


async def handle_hf_summarize(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle hf_summarize tool."""
    text = args.get("text")
    if not text:
        raise ValueError("'text' is required")

    return await hf_inference.summarize(
        text=text,
        model=args.get("model", "facebook/bart-large-cnn"),
        max_length=args.get("max_length", 150),
    )


async def handle_hf_translate(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle hf_translate tool."""
    text = args.get("text")
    if not text:
        raise ValueError("'text' is required")

    return await hf_inference.translate(
        text=text,
        model=args.get("model", "Helsinki-NLP/opus-mt-de-en"),
    )


async def handle_hf_models(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle hf_models tool."""
    task = args.get("task")
    if task:
        models = hf_inference.RECOMMENDED_MODELS.get(task, [])
        return {"task": task, "models": models}
    return {"models": hf_inference.list_recommended_models()}


HF_HANDLERS = {
    "hf_generate": handle_hf_generate,
    "hf_chat": handle_hf_chat,
    "hf_embed": handle_hf_embed,
    "hf_image": handle_hf_image,
    "hf_summarize": handle_hf_summarize,
    "hf_translate": handle_hf_translate,
    "hf_models": handle_hf_models,
}
