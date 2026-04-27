# app/services/txt2img_mcp.py
"""
MCP Tools für Text-to-Image Generierung (Stable Diffusion, FLUX, etc.)

Unterstützt:
- ComfyUI Backend
- CPU-only Mode (langsam aber funktional)
- Intel Arc GPU via OpenVINO (wenn verfügbar)
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ailinux.mcp.txt2img")

# ============================================================================
# MCP Tool Definitions
# ============================================================================

TXT2IMG_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "txt2img_generate",
        "description": "Generate an image from a text prompt using Stable Diffusion. Supports SD 1.5, SDXL, SD 3.5, and FLUX models via ComfyUI.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Text description of the image to generate"
                },
                "negative_prompt": {
                    "type": "string",
                    "description": "What to avoid in the image (e.g., 'blurry, low quality')"
                },
                "width": {
                    "type": "integer",
                    "default": 512,
                    "minimum": 64,
                    "maximum": 2048,
                    "description": "Image width in pixels (must be multiple of 64)"
                },
                "height": {
                    "type": "integer",
                    "default": 512,
                    "minimum": 64,
                    "maximum": 2048,
                    "description": "Image height in pixels (must be multiple of 64)"
                },
                "steps": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 150,
                    "description": "Number of diffusion steps (more = better quality, slower)"
                },
                "cfg_scale": {
                    "type": "number",
                    "default": 7.0,
                    "minimum": 1.0,
                    "maximum": 30.0,
                    "description": "Classifier-free guidance scale (how closely to follow the prompt)"
                },
                "seed": {
                    "type": "integer",
                    "default": -1,
                    "description": "Random seed (-1 for random)"
                },
                "model": {
                    "type": "string",
                    "description": "Model to use (e.g., 'sd15', 'sdxl', 'sd35', 'flux')"
                },
                "sampler": {
                    "type": "string",
                    "default": "euler",
                    "enum": ["euler", "euler_a", "dpm++_2m", "dpm++_sde", "ddim", "lms"],
                    "description": "Sampling method"
                }
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "txt2img_models",
        "description": "List available image generation models and their capabilities",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "txt2img_status",
        "description": "Check if image generation backend (ComfyUI) is available and get hardware info",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "txt2img_queue",
        "description": "Get current image generation queue status",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]


# ============================================================================
# Handler Functions
# ============================================================================

async def handle_txt2img_generate(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate an image from text prompt."""
    from ..services.sd3 import sd3_service
    from ..config import get_settings

    prompt = params.get("prompt")
    if not prompt:
        return {"error": "prompt is required", "success": False}

    # Normalize dimensions to multiples of 64
    width = params.get("width", 512)
    height = params.get("height", 512)
    width = max(64, min(2048, (width // 64) * 64))
    height = max(64, min(2048, (height // 64) * 64))

    try:
        result = await sd3_service.generate_image(
            prompt=prompt,
            negative_prompt=params.get("negative_prompt"),
            width=width,
            height=height,
            steps=params.get("steps", 20),
            cfg_scale=params.get("cfg_scale", 7.0),
            seed=params.get("seed", -1),
            model=params.get("model"),
            sampler_name=params.get("sampler", "euler")
        )

        # Check if we got images
        images = result.get("images", [])
        if images:
            return {
                "success": True,
                "images": images,
                "count": len(images),
                "parameters": {
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "steps": params.get("steps", 20),
                    "cfg_scale": params.get("cfg_scale", 7.0),
                    "seed": params.get("seed", -1)
                }
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "No images generated"),
                "hint": "ComfyUI backend may not be running. Check with txt2img_status."
            }

    except Exception as e:
        logger.exception("Image generation failed: %s", e)
        return {
            "success": False,
            "error": str(e),
            "hint": "Ensure ComfyUI is running and configured in settings"
        }


async def handle_txt2img_models(params: Dict[str, Any]) -> Dict[str, Any]:
    """List available image generation models."""
    from ..config import get_settings

    settings = get_settings()

    # Default models based on configuration
    default_models = []
    if settings.stable_diffusion_default_models:
        default_models = [m.strip() for m in settings.stable_diffusion_default_models.split(",")]

    models = {
        "configured_models": default_models,
        "backend": settings.stable_diffusion_backend or "comfyui",
        "supported_types": [
            {
                "id": "sd15",
                "name": "Stable Diffusion 1.5",
                "description": "Classic SD model, fast, works well on CPU",
                "recommended_size": "512x512",
                "vram_requirement": "4GB (CPU: 8GB RAM)"
            },
            {
                "id": "sdxl",
                "name": "Stable Diffusion XL",
                "description": "Higher quality, larger images",
                "recommended_size": "1024x1024",
                "vram_requirement": "8GB (CPU: 16GB RAM)"
            },
            {
                "id": "sd35",
                "name": "Stable Diffusion 3.5",
                "description": "Latest SD with improved text rendering",
                "recommended_size": "1024x1024",
                "vram_requirement": "12GB (CPU: 24GB RAM)"
            },
            {
                "id": "flux",
                "name": "FLUX.1",
                "description": "State-of-the-art image quality",
                "recommended_size": "1024x1024",
                "vram_requirement": "16GB+ (CPU: 32GB RAM)"
            }
        ]
    }

    return models


async def handle_txt2img_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Check image generation backend status."""
    import httpx
    from ..config import get_settings

    settings = get_settings()
    status = {
        "backend": settings.stable_diffusion_backend or "comfyui",
        "comfyui_url": str(settings.comfyui_url) if settings.comfyui_url else None,
        "sd_url": str(settings.stable_diffusion_url) if settings.stable_diffusion_url else None,
        "available": False,
        "hardware": await _detect_hardware()
    }

    # Check ComfyUI availability
    if settings.comfyui_url:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.comfyui_url}/system_stats")
                if resp.status_code == 200:
                    status["available"] = True
                    status["comfyui_stats"] = resp.json()
        except Exception as e:
            status["comfyui_error"] = str(e)

    # Performance estimate based on hardware
    status["performance_estimate"] = _estimate_performance(status["hardware"])

    return status


async def handle_txt2img_queue(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get ComfyUI queue status."""
    import httpx
    from ..config import get_settings

    settings = get_settings()

    if not settings.comfyui_url:
        return {"error": "ComfyUI not configured", "queue": []}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.comfyui_url}/queue")
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"ComfyUI returned {resp.status_code}"}
    except Exception as e:
        return {"error": str(e), "queue": []}


# ============================================================================
# Helper Functions
# ============================================================================

async def _detect_hardware() -> Dict[str, Any]:
    """Detect available hardware for image generation."""
    import subprocess

    hardware = {
        "cpu": None,
        "ram_gb": 0,
        "gpu": None,
        "gpu_type": None,
        "recommended_backend": "cpu"
    }

    # CPU info
    try:
        result = subprocess.run(
            ["lscpu"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split("\n"):
            if "Model name:" in line:
                hardware["cpu"] = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass

    # RAM
    try:
        result = subprocess.run(
            ["free", "-g"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split("\n"):
            if line.startswith("Mem:"):
                hardware["ram_gb"] = int(line.split()[1])
                break
    except Exception:
        pass

    # GPU detection
    try:
        result = subprocess.run(
            ["lspci"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.lower().split("\n"):
            if "vga" in line or "3d" in line:
                if "nvidia" in line:
                    hardware["gpu"] = "NVIDIA"
                    hardware["gpu_type"] = "cuda"
                    hardware["recommended_backend"] = "cuda"
                elif "intel" in line and ("arc" in line or "graphics" in line):
                    hardware["gpu"] = "Intel Arc/Integrated"
                    hardware["gpu_type"] = "intel"
                    hardware["recommended_backend"] = "openvino"
                elif "amd" in line or "radeon" in line:
                    hardware["gpu"] = "AMD"
                    hardware["gpu_type"] = "rocm"
                    hardware["recommended_backend"] = "rocm"
                break
    except Exception:
        pass

    return hardware


def _estimate_performance(hardware: Dict[str, Any]) -> Dict[str, Any]:
    """Estimate image generation performance based on hardware."""
    estimates = {
        "sd15_512x512": "unknown",
        "sdxl_1024x1024": "unknown",
        "recommendation": ""
    }

    gpu_type = hardware.get("gpu_type")
    ram_gb = hardware.get("ram_gb", 0)
    cpu = hardware.get("cpu", "").lower()

    # Intel Arc / Integrated (Arrow Lake etc.)
    if gpu_type == "intel":
        estimates["sd15_512x512"] = "30-60 sec (OpenVINO optimized)"
        estimates["sdxl_1024x1024"] = "2-5 min (OpenVINO optimized)"
        estimates["recommendation"] = (
            "Intel Arc/Integrated detected. Install OpenVINO for best performance:\n"
            "  pip install openvino optimum[openvino]\n"
            "  Use SD 1.5 models for faster generation."
        )

    # CPU-only with Intel
    elif "intel" in cpu and "ultra" in cpu:
        estimates["sd15_512x512"] = "2-4 min (CPU, 20 cores)"
        estimates["sdxl_1024x1024"] = "8-15 min (CPU)"
        estimates["recommendation"] = (
            "Intel Core Ultra detected with integrated Arc GPU.\n"
            "For MUCH faster generation, use OpenVINO:\n"
            "  pip install openvino optimum[openvino]\n"
            "  This can reduce SD 1.5 to ~30-60 seconds!"
        )

    # Generic CPU
    elif ram_gb >= 16:
        estimates["sd15_512x512"] = "3-8 min (CPU only)"
        estimates["sdxl_1024x1024"] = "15-30 min (CPU only)"
        estimates["recommendation"] = (
            "CPU-only mode detected. For better performance:\n"
            "  - Use SD 1.5 models (fastest on CPU)\n"
            "  - Reduce steps to 15-20\n"
            "  - Use smaller image sizes (512x512)"
        )
    else:
        estimates["sd15_512x512"] = "5-15 min (limited RAM)"
        estimates["sdxl_1024x1024"] = "Not recommended (RAM < 16GB)"
        estimates["recommendation"] = (
            "Limited RAM detected. Stick to SD 1.5 at 512x512."
        )

    return estimates


# ============================================================================
# Handler Map (for mcp_service.py integration)
# ============================================================================

TXT2IMG_HANDLERS: Dict[str, Any] = {
    "txt2img_generate": handle_txt2img_generate,
    "txt2img_models": handle_txt2img_models,
    "txt2img_status": handle_txt2img_status,
    "txt2img_queue": handle_txt2img_queue,
}
