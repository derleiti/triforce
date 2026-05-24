from __future__ import annotations

import base64
import httpx
import logging
import json
from typing import Any, Dict, Optional

from ..config import get_settings
from ..utils.errors import api_error
from ..utils.http_client import HttpClient

logger = logging.getLogger("ailinux.sd3.service")

class StableDiffusionService:
    def __init__(self):
        self._client: Optional[HttpClient] = None # For Automatic1111
        self._base_url: Optional[str] = None # For Automatic1111
        self._comfyui_client: Optional[HttpClient] = None
        self._comfyui_base_url: Optional[str] = None
        self._username: Optional[str] = None
        self._password: Optional[str] = None

    def _ensure_client(self):
        settings = get_settings()

        if settings.stable_diffusion_backend == "automatic1111":
            if not settings.stable_diffusion_url:
                raise api_error("Stable Diffusion URL is not configured for Automatic1111", status_code=503, code="sd_unavailable")
            if not self._client:
                self._base_url = str(settings.stable_diffusion_url)
                self._username = settings.stable_diffusion_username
                self._password = settings.stable_diffusion_password
                self._client = HttpClient(timeout=settings.request_timeout)
        elif settings.stable_diffusion_backend == "comfyui":
            if not settings.comfyui_url:
                raise api_error("ComfyUI URL is not configured", status_code=503, code="comfyui_unavailable")
            if not self._comfyui_client:
                self._comfyui_base_url = str(settings.comfyui_url)
                self._username = settings.stable_diffusion_username
                self._password = settings.stable_diffusion_password
                self._comfyui_client = HttpClient(timeout=settings.request_timeout)
        else:
            raise api_error(f"Unknown Stable Diffusion backend: {settings.stable_diffusion_backend}", status_code=500, code="sd_backend_unknown")

    async def generate_image(self, prompt: str, negative_prompt: Optional[str] = None,
                               width: int = 512, height: int = 512,
                               steps: int = 20, cfg_scale: float = 7.0,
                               sampler_name: str = "Euler a",
                               seed: int = -1, model: Optional[str] = None) -> Dict[str, Any]:
        self._ensure_client()
        settings = get_settings()

        try:
            if settings.stable_diffusion_backend == "automatic1111":
                return await self._generate_image_automatic1111(prompt, negative_prompt, width, height, steps, cfg_scale, sampler_name, seed, model)
            elif settings.stable_diffusion_backend == "comfyui":
                return await self._generate_image_comfyui(prompt, negative_prompt, width, height, steps, cfg_scale, sampler_name, seed, model)
            else:
                raise api_error(f"Unknown Stable Diffusion backend: {settings.stable_diffusion_backend}", status_code=500, code="sd_backend_unknown")
        except Exception as exc:
            logger.error(f"Image generation failed: {exc}", exc_info=True)
            # Return empty images array with error message for frontend compatibility
            return {
                "images": [],
                "error": f"Image generation service is currently unavailable. Backend: {settings.stable_diffusion_backend}. Please try again later or contact support."
            }

    async def _generate_image_automatic1111(self, prompt: str, negative_prompt: Optional[str] = None,
                                              width: int = 512, height: int = 512,
                                              steps: int = 20, cfg_scale: float = 7.0,
                                              sampler_name: str = "Euler a",
                                              seed: int = -1, model: Optional[str] = None) -> Dict[str, Any]:
        if not self._base_url:
            logger.error("Automatic1111 base URL not configured")
            return {"images": [], "error": "Automatic1111 backend is not properly configured"}

        if not self._client:
            logger.error("Automatic1111 client not initialized")
            return {"images": [], "error": "Automatic1111 backend is not available"}

        settings = get_settings()

        # Construct payload for Stable Diffusion API (e.g., Automatic1111 compatible)
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "sampler_name": sampler_name,
            "seed": seed,
            "batch_size": 1, # Always generate one image for now
        }
        if model:
            payload["sd_model_checkpoint"] = model
        elif settings.stable_diffusion_default_models:
            payload["sd_model_checkpoint"] = settings.stable_diffusion_default_models

        headers = {}
        if self._username and self._password:
            auth_string = f"{self._username}:{self._password}"
            encoded_auth = auth_string.encode("ascii")
            headers["Authorization"] = f"Basic {encoded_auth.decode("ascii")}"

        # The actual endpoint might vary, common is /sdapi/v1/txt2img
        url = httpx.URL(self._base_url).join("/sdapi/v1/txt2img")

        try:
            response = await self._client.post(
                str(url),
                headers=headers,
                json=payload,
                timeout=self._client.timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.exception("Error generating image with Automatic1111: %s", exc)
            raise api_error(
                f"Automatic1111 image generation failed: {exc}",
                status_code=500,
                code="sd_generation_failed",
            ) from exc

    async def _generate_image_comfyui(self, prompt: str, negative_prompt: Optional[str] = None,
                                        width: int = 512, height: int = 512,
                                        steps: int = 20, cfg_scale: float = 7.0,
                                        sampler_name: str = "Euler a",
                                        seed: int = -1, model: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"DEBUG: _generate_image_comfyui called with prompt: {prompt}")

        if not self._comfyui_client or not self._comfyui_base_url:
            logger.error("ComfyUI client not initialized.")
            raise RuntimeError("ComfyUI client not initialized.")

        settings = get_settings()

        # Model selection with fallback for memory constraints
        if not model:
            # Try SDXL first, then fallback to SD 1.5 if memory issues
            available_models = settings.stable_diffusion_default_models.split(',') if settings.stable_diffusion_default_models else []
            model = available_models[0].strip() if available_models else None

        if not model:
            raise api_error("No Stable Diffusion model specified for ComfyUI.", status_code=400, code="comfyui_no_model")

        logger.info(f"DEBUG: Using model: {model}")

        # Try SDXL first, fallback to SD 1.5 on memory failure
        try:
            return await self._generate_with_workflow(prompt, negative_prompt, width, height, steps, cfg_scale, sampler_name, seed, model)
        except Exception as exc:
            logger.warning(f"Primary model {model} failed, attempting fallback: {exc}")

            # Check if this looks like a memory error and try SD 1.5 fallback
            error_msg = str(exc).lower()
            if "memory" in error_msg or "out of memory" in error_msg or "cuda" in error_msg:
                # Try SD 1.5 models as fallback
                sd15_models = ["v1-5-pruned-emaonly.safetensors", "v1-5-pruned.safetensors", "runwayml/stable-diffusion-v1-5"]
                for fallback_model in sd15_models:
                    try:
                        logger.info(f"Trying SD 1.5 fallback model: {fallback_model}")
                        return await self._generate_with_workflow(prompt, negative_prompt, width, height, steps, cfg_scale, sampler_name, seed, fallback_model)
                    except Exception as fallback_exc:
                        logger.warning(f"Fallback model {fallback_model} also failed: {fallback_exc}")
                        continue

            # If we get here, all models failed - re-raise original exception
            raise exc

    async def _generate_with_workflow(self, prompt: str, negative_prompt: Optional[str] = None,
                                     width: int = 512, height: int = 512,
                                     steps: int = 20, cfg_scale: float = 7.0,
                                     sampler_name: str = "Euler a",
                                     seed: int = -1, model: str = None) -> Dict[str, Any]:
        """Generate image with ComfyUI workflow, supporting both SDXL and SD 1.5 models."""

        # Detect model type for appropriate workflow
        is_sdxl = "xl" in model.lower() or "sdxl" in model.lower()

        if is_sdxl:
            # SDXL workflow with refiner (if available)
            workflow = self._create_sdxl_workflow(prompt, negative_prompt, width, height, steps, cfg_scale, seed, model)
        else:
            # SD 1.5 workflow (simpler, less memory intensive)
            workflow = self._create_sd15_workflow(prompt, negative_prompt, width, height, steps, cfg_scale, seed, model)

        headers = {}
        if self._username and self._password:
            auth_string = f"{self._username}:{self._password}"
            encoded_auth = base64.b64encode(auth_string.encode("ascii")).decode("ascii")
            headers["Authorization"] = f"Basic {encoded_auth}"

        # Use httpx.URL to properly construct the endpoint URL
        url = httpx.URL(self._comfyui_base_url).join("/prompt")

        try:
            logger.info(f"DEBUG: About to submit prompt to ComfyUI at {url} with model {model}")
            response = await self._comfyui_client.post(
                str(url),
                headers=headers,
                json={"prompt": workflow, "client_id": "ailinux_backend"},
                timeout=self._comfyui_client.timeout,
            )

            # Log the full response for debugging
            logger.info(f"ComfyUI response status: {response.status_code}")
            logger.info(f"ComfyUI response body: {response.text}")

            response.raise_for_status()

            # ComfyUI's /prompt endpoint returns a prompt_id.
            response_data = response.json()
            prompt_id = response_data.get("prompt_id")

            logger.info(f"ComfyUI prompt submitted. Prompt ID: {prompt_id}")

            # Poll for completion and get the actual image
            logger.info(f"Starting polling for prompt_id: {prompt_id}")
            image_data = await self._poll_for_image_completion(prompt_id, headers)
            return image_data

        except Exception as exc:
            logger.exception("Error generating image with ComfyUI workflow: %s", exc)
            raise api_error(
                f"ComfyUI image generation failed: {exc}",
                status_code=500,
                code="comfyui_generation_failed",
            ) from exc

    def _create_sd15_workflow(self, prompt: str, negative_prompt: Optional[str], width: int, height: int,
                             steps: int, cfg_scale: float, seed: int, model: str) -> Dict[str, Any]:
        """Create ComfyUI workflow for SD 1.5 models (lower memory usage)."""
        return {
            "1": {
                "inputs": {
                    "ckpt_name": model
                },
                "class_type": "CheckpointLoaderSimple",
                "_meta": {"title": "Load Checkpoint"}
            },
            "2": {
                "inputs": {
                    "text": prompt,
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Positive)"}
            },
            "3": {
                "inputs": {
                    "text": negative_prompt if negative_prompt else "",
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Negative)"}
            },
            "4": {
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage",
                "_meta": {"title": "Empty Latent Image"}
            },
            "5": {
                "inputs": {
                    "seed": seed if seed >= 0 else 0,
                    "steps": steps,
                    "cfg": cfg_scale,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0]
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            },
            "6": {
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["1", 2]
                },
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE Decode"}
            },
            "7": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["6", 0]
                },
                "class_type": "SaveImage",
                "_meta": {"title": "Save Image"}
            }
        }

    def _create_sdxl_workflow(self, prompt: str, negative_prompt: Optional[str], width: int, height: int,
                             steps: int, cfg_scale: float, seed: int, model: str) -> Dict[str, Any]:
        """Create ComfyUI workflow for SDXL models (higher quality but more memory intensive)."""
        return {
            "1": {
                "inputs": {
                    "ckpt_name": model
                },
                "class_type": "CheckpointLoaderSimple",
                "_meta": {"title": "Load Checkpoint"}
            },
            "2": {
                "inputs": {
                    "text": prompt,
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Positive)"}
            },
            "3": {
                "inputs": {
                    "text": negative_prompt if negative_prompt else "",
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Negative)"}
            },
            "4": {
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage",
                "_meta": {"title": "Empty Latent Image"}
            },
            "5": {
                "inputs": {
                    "seed": seed if seed >= 0 else 0,
                    "steps": steps,
                    "cfg": cfg_scale,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0]
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            },
            "6": {
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["1", 2]
                },
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE Decode"}
            },
            "7": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["6", 0]
                },
                "class_type": "SaveImage",
                "_meta": {"title": "Save Image"}
            }
        }

    async def _poll_for_image_completion(self, prompt_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Poll ComfyUI history endpoint until image generation is complete."""
        import asyncio
        import base64

        logger.info(f"DEBUG: _poll_for_image_completion called with prompt_id: {prompt_id}")

        if not self._comfyui_client or not self._comfyui_base_url:
            logger.error("ComfyUI client not initialized for polling.")
            raise RuntimeError("ComfyUI client not initialized for polling.")

        logger.info(f"Starting polling for prompt_id: {prompt_id}")
        max_attempts = 300  # 5 minutes max wait for SDXL generation
        poll_interval = 2.0  # Check every 2 seconds



        for attempt in range(max_attempts):
            try:
                logger.info(f"Polling attempt {attempt + 1}/{max_attempts}")
                # Check history for this prompt_id
                history_url = httpx.URL(self._comfyui_base_url).join("/history")
                response = await self._comfyui_client.get(
                    str(history_url),
                    headers=headers,
                    timeout=self._comfyui_client.timeout,
                )

                if response.status_code == 200:
                    history_data = response.json()
                    logger.info(f"Polling attempt {attempt + 1}: History contains {len(history_data)} entries")



                    # Check if our prompt_id is in the history and completed
                    if prompt_id in history_data:
                        logger.info(f"Found prompt_id {prompt_id} in history")
                        prompt_history = history_data[prompt_id]
                        status_info = prompt_history.get("status", {})
                        logger.info(f"Prompt history status: {status_info}")
                        logger.info(f"Prompt history has outputs: {'outputs' in prompt_history}")

                        # Check status string
                        status_str = status_info.get("status_str", "unknown")
                        logger.info(f"Status string: {status_str}")

                        # Check if generation is complete (has outputs)
                        if "outputs" in prompt_history and prompt_history["outputs"]:
                            logger.info(f"Found outputs for prompt_id {prompt_id}")
                            outputs = prompt_history["outputs"]

                            # Find the SaveImage node output (usually node "7" in our workflow)
                            for node_id, node_output in outputs.items():
                                if "images" in node_output:
                                    images = node_output["images"]
                                    if images:
                                        # Get the first image
                                        image_info = images[0]

                                        # ComfyUI provides images via /view endpoint
                                        image_filename = image_info.get("filename")
                                        if image_filename:
                                            image_url = f"{self._comfyui_base_url}/view?filename={image_filename}&subfolder=&type=output"

                                            # Optionally download the image data
                                            try:
                                                image_response = await self._comfyui_client.get(
                                                    image_url,
                                                    headers=headers,
                                                    timeout=self._comfyui_client.timeout,
                                                )

                                                if image_response.status_code == 200:
                                                    # Convert to base64 for frontend
                                                    image_b64 = base64.b64encode(image_response.content).decode('utf-8')
                                                    image_data_url = f"data:image/png;base64,{image_b64}"

                                                    logger.info(f"Image generation completed for prompt_id: {prompt_id}")
                                                    return {
                                                        "images": [image_data_url]
                                                    }
                                            except Exception as img_exc:
                                                logger.warning(f"Failed to download image: {img_exc}")

                            # If we get here, outputs exist but no images found
                            logger.info(f"Generation completed but no images found for prompt_id: {prompt_id}")
                            return {
                                "images": []
                            }

                        elif status_str == "error" or status_info.get("completed") == False:
                            # Generation failed - return empty array with error message
                            error_msg = status_info.get("msg", "Unknown error")
                            logger.warning(f"Image generation failed for prompt_id {prompt_id}: {error_msg} - returning empty array")
                            return {
                                "images": [],
                                "error": f"Image generation failed: {error_msg}"
                            }

                        else:
                            # Prompt found but not complete and not error - might be processing
                            logger.info(f"Prompt {prompt_id} status: {status_str} - continuing to poll")

                    else:
                        # Prompt not found in history yet - continue polling
                        logger.info(f"Prompt_id {prompt_id} not found in history (contains {len(history_data)} entries) - continuing to poll")

                        # If we've been polling for more than 3 attempts and prompt is still not in history,
                        # assume ComfyUI is not working and return empty array
                        if attempt > 3:
                            logger.warning(f"Prompt {prompt_id} not found in history after {attempt} attempts - ComfyUI may be failing, returning empty array")
                            return {
                                "images": []
                            }

                # Wait before next poll
                await asyncio.sleep(poll_interval)

            except Exception as poll_exc:
                logger.warning(f"Error polling ComfyUI history (attempt {attempt + 1}): {poll_exc}")
                await asyncio.sleep(poll_interval)

        # Timeout - return empty array instead of error
        logger.error(f"Image generation timeout for prompt_id: {prompt_id}")
        return {
            "images": []
        }

sd3_service = StableDiffusionService()
