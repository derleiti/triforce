"""
ComfyUI Client for AILinux Backend

A dedicated client for interacting with ComfyUI API endpoints.
Provides high-level functions for submitting prompts, waiting for results,
and downloading generated images.
"""

import asyncio
import base64
import httpx
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

logger = logging.getLogger("ailinux.comfy_client")


class ComfyUIClient:
    """Client for interacting with ComfyUI API."""

    def __init__(self, base_url: str, username: Optional[str] = None, password: Optional[str] = None, timeout: int = 1800):
        """
        Initialize ComfyUI client.

        Args:
            base_url: Base URL of ComfyUI server (e.g., "http://localhost:8188")
            username: Optional username for authentication
            password: Optional password for authentication
            timeout: Request timeout in seconds (default 1800s = 30 min for 4K generations)
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers if credentials are provided."""
        headers = {}
        if self.username and self.password:
            auth_string = f"{self.username}:{self.password}"
            encoded_auth = base64.b64encode(auth_string.encode("ascii")).decode("ascii")
            headers["Authorization"] = f"Basic {encoded_auth}"
        return headers

    async def submit_prompt(self, workflow: Dict[str, Any], client_id: str = "ailinux_backend") -> str:
        """
        Submit a workflow prompt to ComfyUI.

        Args:
            workflow: ComfyUI workflow JSON
            client_id: Client identifier

        Returns:
            Prompt ID for tracking the job

        Raises:
            Exception: If prompt submission fails
        """
        url = urljoin(self.base_url, "/prompt")
        headers = self._get_auth_headers()

        payload = {
            "prompt": workflow,
            "client_id": client_id
        }

        logger.info(f"Submitting prompt to ComfyUI at {url}")
        try:
            response = await self.client.post(
                url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            prompt_id = data.get("prompt_id")

            if not prompt_id:
                raise Exception("No prompt_id returned from ComfyUI")

            logger.info(f"Prompt submitted successfully. Prompt ID: {prompt_id}")
            return prompt_id

        except Exception as e:
            logger.error(f"Failed to submit prompt: {e}")
            raise

    async def wait_for_result(self, prompt_id: str, poll_interval: int = 2, max_wait: int = 1800) -> Dict[str, Any]:
        """
        Wait for a prompt to complete and return the result.

        Args:
            prompt_id: The prompt ID to wait for
            poll_interval: Seconds between status checks
            max_wait: Maximum time to wait in seconds (default 1800s = 30 min for 4K generations)

        Returns:
            History data containing the completed job information

        Raises:
            TimeoutError: If job doesn't complete within max_wait
            Exception: If job fails or other error occurs
        """
        url = urljoin(self.base_url, "/history")
        headers = self._get_auth_headers()

        elapsed = 0
        while elapsed < max_wait:
            try:
                response = await self.client.get(url, headers=headers)
                response.raise_for_status()

                history = response.json()

                if prompt_id in history:
                    job_data = history[prompt_id]
                    status = job_data.get("status", {})

                    if status.get("completed", False):
                        logger.info(f"Job {prompt_id} completed successfully")
                        return job_data
                    else:
                        status_str = (status.get("status_str") or "").lower()
                        error_msg = status.get("error")
                        if status_str == "error" or error_msg:
                            if not error_msg:
                                for message in status.get("messages", []):
                                    if isinstance(message, list) and len(message) == 2 and message[0] == "execution_error":
                                        error_msg = message[1].get("exception_message", "Unknown error")
                                        break
                            error_msg = error_msg or status_str or "Unknown error"
                            logger.error(f"Job {prompt_id} failed: {error_msg}")
                            raise Exception(f"ComfyUI job failed: {error_msg}")

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            except Exception as e:
                logger.error(f"Error checking job status: {e}")
                raise

        raise TimeoutError(f"Job {prompt_id} did not complete within {max_wait} seconds")

    async def download_output_image(self, filename: str, subfolder: str = "", image_type: str = "output") -> bytes:
        """
        Download a generated image from ComfyUI.

        Args:
            filename: Name of the image file
            subfolder: Subfolder path (optional)
            image_type: Type of image ("output", "input", "temp")

        Returns:
            Image data as bytes

        Raises:
            Exception: If download fails
        """
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": image_type
        }

        url = urljoin(self.base_url, "/view")
        headers = self._get_auth_headers()

        logger.info(f"Downloading image: {filename}")
        try:
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()

            logger.info(f"Image downloaded successfully: {len(response.content)} bytes")
            return response.content

        except Exception as e:
            logger.error(f"Failed to download image {filename}: {e}")
            raise

    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status from ComfyUI.

        Returns:
            Queue status information
        """
        url = urljoin(self.base_url, "/queue")
        headers = self._get_auth_headers()

        try:
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Convenience functions for common workflows
async def create_minimal_workflow(prompt: str, negative_prompt: str = "", width: int = 512, height: int = 512,
                                 steps: int = 20, cfg_scale: float = 7.0, seed: int = -1,
                                 model_name: str = "v1-5-pruned-emaonly.safetensors") -> Dict[str, Any]:
    """
    Create a minimal ComfyUI workflow for text-to-image generation.

    This creates a basic SD 1.5 workflow. For SDXL, use create_sdxl_workflow instead.
    """
    # Generate random seed if not provided
    if seed == -1:
        import random
        seed = random.randint(0, 2**32 - 1)

    positive_text = prompt or ""
    negative_text = negative_prompt or ""

    workflow = {
        "1": {
            "inputs": {
                "ckpt_name": model_name
            },
            "class_type": "CheckpointLoaderSimple",
            "_meta": {
                "title": "Load Checkpoint"
            }
        },
        "2": {
            "inputs": {
                "text": prompt,
                "clip": ["1", 1]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {
                "title": "Positive Prompt"
            }
        },
        "3": {
            "inputs": {
                "text": negative_prompt,
                "clip": ["1", 1]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {
                "title": "Negative Prompt"
            }
        },
        "4": {
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg_scale,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler",
            "_meta": {
                "title": "KSampler"
            }
        },
        "5": {
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage",
            "_meta": {
                "title": "Empty Latent Image"
            }
        },
        "6": {
            "inputs": {
                "samples": ["4", 0],
                "vae": ["1", 2]
            },
            "class_type": "VAEDecode",
            "_meta": {
                "title": "VAE Decode"
            }
        },
        "7": {
            "inputs": {
                "filename_prefix": "ComfyUI",
                "images": ["6", 0]
            },
            "class_type": "SaveImage",
            "_meta": {
                "title": "Save Image"
            }
        }
    }

    return workflow


async def create_sdxl_workflow(prompt: str, negative_prompt: str = "", width: int = 1024, height: int = 1024,
                              steps: int = 20, cfg_scale: float = 7.0, seed: int = -1,
                              model_name: str = "sdXL_v10VAEFix.safetensors") -> Dict[str, Any]:
    """
    Create an SDXL workflow for ComfyUI.

    Note: This requires SDXL models and may need more VRAM.
    """
    # Generate random seed if not provided
    if seed == -1:
        import random
        seed = random.randint(0, 2**32 - 1)

    positive_text = prompt or ""
    negative_text = negative_prompt or ""

    workflow = {
        "1": {
            "inputs": {
                "ckpt_name": model_name
            },
            "class_type": "CheckpointLoaderSimple",
            "_meta": {
                "title": "Load SDXL Checkpoint"
            }
        },
        "2": {
            "inputs": {
                "text": prompt,
                "clip": ["1", 1]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {
                "title": "Positive Prompt"
            }
        },
        "3": {
            "inputs": {
                "text": negative_prompt,
                "clip": ["1", 1]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {
                "title": "Negative Prompt"
            }
        },
        "4": {
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg_scale,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler",
            "_meta": {
                "title": "KSampler"
            }
        },
        "5": {
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage",
            "_meta": {
                "title": "Empty Latent Image"
            }
        },
        "6": {
            "inputs": {
                "samples": ["4", 0],
                "vae": ["1", 2]
            },
            "class_type": "VAEDecode",
            "_meta": {
                "title": "VAE Decode"
            }
        },
        "7": {
            "inputs": {
                "filename_prefix": "ComfyUI_SDXL",
                "images": ["6", 0]
            },
            "class_type": "SaveImage",
            "_meta": {
                "title": "Save Image"
            }
        }
    }

    return workflow


async def create_sd35_workflow(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 30,
    cfg_scale: float = 6.0,
    seed: int = -1,
    model_name: str = "sd3.5_large.safetensors",
    clip_g_name: str = "clip_g_sd35.safetensors",
    clip_l_name: str = "clip_l_sd35.safetensors",
    t5_name: str = "t5xxl_fp16_sd35.safetensors",  # Using fp16 for better quality with 24GB VRAM
) -> Dict[str, Any]:
    """
    Create an SD 3.5 workflow for ComfyUI.

    The SD 3.5 checkpoints ship with external CLIP and T5 encoders, so we load
    them explicitly via TripleCLIPLoader and use the SD3 latent/image nodes.
    """
    if seed == -1:
        import random
        seed = random.randint(0, 2**32 - 1)

    positive_text = prompt or ""
    negative_text = negative_prompt or ""

    workflow = {
        "1": {
            "inputs": {
                "ckpt_name": model_name
            },
            "class_type": "CheckpointLoaderSimple",
            "_meta": {"title": "Load SD3.5 Checkpoint"}
        },
        "2": {
            "inputs": {
                "model": ["1", 0],
                "shift": 3
            },
            "class_type": "ModelSamplingSD3",
            "_meta": {"title": "Model Sampling SD3"}
        },
        "3": {
            "inputs": {
                "clip_name1": clip_g_name,
                "clip_name2": clip_l_name,
                "clip_name3": t5_name
            },
            "class_type": "TripleCLIPLoader",
            "_meta": {"title": "Triple CLIP Loader"}
        },
        "4": {
            "inputs": {
                "clip": ["3", 0],
                "clip_l": positive_text,
                "clip_g": positive_text,
                "t5xxl": positive_text,
                "empty_padding": "empty_prompt"
            },
            "class_type": "CLIPTextEncodeSD3",
            "_meta": {"title": "Positive Prompt"}
        },
        "5": {
            "inputs": {
                "clip": ["3", 0],
                "clip_l": negative_text,
                "clip_g": negative_text,
                "t5xxl": negative_text,
                "empty_padding": "empty_prompt"
            },
            "class_type": "CLIPTextEncodeSD3",
            "_meta": {"title": "Negative Prompt"}
        },
        "6": {
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            },
            "class_type": "EmptySD3LatentImage",
            "_meta": {"title": "Empty SD3 Latent"}
        },
        "7": {
            "inputs": {
                "model": ["2", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["6", 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg_scale,
                "sampler_name": "dpmpp_2m",
                "scheduler": "sgm_uniform",
                "denoise": 1.0
            },
            "class_type": "KSampler",
            "_meta": {"title": "SD3.5 KSampler"}
        },
        "8": {
            "inputs": {
                "samples": ["7", 0],
                "vae": ["1", 2]
            },
            "class_type": "VAEDecode",
            "_meta": {"title": "VAE Decode"}
        },
        "9": {
            "inputs": {
                "filename_prefix": "ComfyUI",
                "images": ["8", 0]
            },
            "class_type": "SaveImage",
            "_meta": {"title": "Save Image"}
        }
    }

    return workflow
