"""
Hybrid Compute Service - Server + Client GPU Sharing
=====================================================

Verteilt Rechenarbeit zwischen Server und Client:
- Server: Schwere Modelle, große Batches (CUDA/ROCm)
- Client: Leichte Operationen, Embeddings (WebGPU/WebGL)

Protokoll:
1. Client meldet seine GPU-Fähigkeiten (WebGPU, WebGL, WASM)
2. Server entscheidet über Task-Verteilung
3. Client führt lokale Operationen aus
4. Ergebnisse werden kombiniert

WebGPU Models (Client-Side):
- Transformers.js (HuggingFace in Browser)
- ONNX Runtime Web
- TensorFlow.js
- MediaPipe
"""

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger("ailinux.hybrid_compute")


class ClientCapability(Enum):
    """Client-seitige Compute-Fähigkeiten"""
    WEBGPU = auto()          # Modern WebGPU API
    WEBGL2 = auto()          # WebGL 2.0
    WEBGL = auto()           # WebGL 1.0
    WASM_SIMD = auto()       # WebAssembly SIMD
    WASM = auto()            # Basic WebAssembly
    JS_ONLY = auto()         # Pure JavaScript


class TaskLocation(Enum):
    """Wo soll der Task ausgeführt werden"""
    SERVER = "server"        # Nur Server
    CLIENT = "client"        # Nur Client
    HYBRID = "hybrid"        # Beide (Split)
    CLIENT_PREFERRED = "client_preferred"  # Client wenn möglich
    SERVER_PREFERRED = "server_preferred"  # Server wenn möglich


@dataclass
class ClientGPUInfo:
    """GPU-Information vom Client"""
    capability: ClientCapability
    gpu_vendor: str = ""
    gpu_name: str = ""
    max_buffer_size: int = 0
    max_texture_size: int = 0
    supports_f16: bool = False
    supports_storage_buffers: bool = False
    estimated_tflops: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientGPUInfo":
        cap_str = data.get("capability", "JS_ONLY").upper()
        try:
            cap = ClientCapability[cap_str]
        except KeyError:
            cap = ClientCapability.JS_ONLY

        return cls(
            capability=cap,
            gpu_vendor=data.get("gpu_vendor", ""),
            gpu_name=data.get("gpu_name", ""),
            max_buffer_size=data.get("max_buffer_size", 0),
            max_texture_size=data.get("max_texture_size", 0),
            supports_f16=data.get("supports_f16", False),
            supports_storage_buffers=data.get("supports_storage_buffers", False),
            estimated_tflops=data.get("estimated_tflops", 0.0),
        )


@dataclass
class ComputeTask:
    """Beschreibt einen Compute-Task"""
    task_type: str
    input_data: Any
    model_id: Optional[str] = None
    priority: int = 5
    max_tokens: int = 512
    temperature: float = 0.7

    # Task-spezifische Parameter
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskAssignment:
    """Zuordnung eines Tasks zu Server/Client"""
    task: ComputeTask
    location: TaskLocation
    client_model: Optional[str] = None  # WebGPU Model für Client
    server_model: Optional[str] = None  # Server Model
    client_instructions: Optional[Dict[str, Any]] = None
    reason: str = ""


class HybridComputeRouter:
    """
    Entscheidet welche Tasks Server-seitig und welche Client-seitig
    ausgeführt werden sollen.
    """

    # Models die Client-seitig mit WebGPU laufen können
    CLIENT_MODELS = {
        # Embeddings (klein, schnell)
        "embedding_small": {
            "transformers_js": "Xenova/all-MiniLM-L6-v2",
            "onnx_web": "all-MiniLM-L6-v2.onnx",
            "min_capability": ClientCapability.WEBGPU,
            "fallback_capability": ClientCapability.WASM_SIMD,
        },
        "embedding_multilingual": {
            "transformers_js": "Xenova/paraphrase-multilingual-MiniLM-L12-v2",
            "min_capability": ClientCapability.WEBGPU,
        },
        # Text Classification
        "sentiment": {
            "transformers_js": "Xenova/distilbert-base-uncased-finetuned-sst-2-english",
            "min_capability": ClientCapability.WEBGPU,
        },
        # Summarization (klein)
        "summarize_small": {
            "transformers_js": "Xenova/distilbart-cnn-6-6",
            "min_capability": ClientCapability.WEBGPU,
        },
        # Image (CLIP, etc.)
        "clip_embed": {
            "transformers_js": "Xenova/clip-vit-base-patch32",
            "min_capability": ClientCapability.WEBGPU,
        },
        # Speech
        "whisper_tiny": {
            "transformers_js": "Xenova/whisper-tiny",
            "min_capability": ClientCapability.WEBGPU,
        },
    }

    # Tasks die immer Server-seitig laufen
    SERVER_ONLY_TASKS = {
        "llm_generation",       # LLM Text Generation
        "image_generation",     # Stable Diffusion etc.
        "code_completion",      # Code Models
        "rag_retrieval",        # RAG mit großen Indices
        "fine_tuning",          # Model Training
    }

    # Tasks die Client-seitig bevorzugt werden
    CLIENT_PREFERRED_TASKS = {
        "embedding",            # Text Embeddings
        "sentiment_analysis",   # Sentiment
        "text_classification",  # Klassifizierung
        "tokenization",         # Tokenisierung
        "image_embedding",      # CLIP Embeddings
    }

    def __init__(self):
        self._server_load = 0.0
        self._client_sessions: Dict[str, ClientGPUInfo] = {}

    def register_client(self, session_id: str, gpu_info: ClientGPUInfo) -> Dict[str, Any]:
        """Registriert Client und gibt verfügbare Client-Modelle zurück"""
        self._client_sessions[session_id] = gpu_info

        available_models = []
        for model_id, config in self.CLIENT_MODELS.items():
            min_cap = config.get("min_capability", ClientCapability.WEBGPU)
            fallback_cap = config.get("fallback_capability")

            # Prüfe ob Client das Model unterstützt
            if gpu_info.capability.value <= min_cap.value:
                available_models.append({
                    "id": model_id,
                    "transformers_js": config.get("transformers_js"),
                    "onnx_web": config.get("onnx_web"),
                    "backend": "webgpu",
                })
            elif fallback_cap and gpu_info.capability.value <= fallback_cap.value:
                available_models.append({
                    "id": model_id,
                    "transformers_js": config.get("transformers_js"),
                    "backend": "wasm",
                })

        logger.info(f"Client {session_id} registered: {gpu_info.capability.name}, "
                   f"{len(available_models)} models available")

        return {
            "session_id": session_id,
            "capability": gpu_info.capability.name,
            "available_models": available_models,
            "instructions": self._get_client_init_instructions(gpu_info),
        }

    def _get_client_init_instructions(self, gpu_info: ClientGPUInfo) -> Dict[str, Any]:
        """Gibt Initialisierungsanweisungen für Client zurück"""
        if gpu_info.capability == ClientCapability.WEBGPU:
            return {
                "backend": "webgpu",
                "init_script": """
                    import { pipeline } from '@xenova/transformers';
                    // WebGPU Backend aktivieren
                    env.backends.onnx.wasm.numThreads = navigator.hardwareConcurrency;
                    env.backends.onnx.webgpu.enabled = true;
                """,
                "preload_models": ["embedding_small"],
            }
        elif gpu_info.capability in (ClientCapability.WEBGL2, ClientCapability.WEBGL):
            return {
                "backend": "webgl",
                "init_script": """
                    import { pipeline } from '@xenova/transformers';
                    env.backends.onnx.webgl.enabled = true;
                """,
                "preload_models": ["embedding_small"],
            }
        else:
            return {
                "backend": "wasm",
                "init_script": """
                    import { pipeline } from '@xenova/transformers';
                    env.backends.onnx.wasm.numThreads = navigator.hardwareConcurrency;
                """,
                "preload_models": [],
            }

    def route_task(
        self,
        task: ComputeTask,
        session_id: Optional[str] = None,
        force_location: Optional[TaskLocation] = None,
    ) -> TaskAssignment:
        """
        Entscheidet wo ein Task ausgeführt werden soll.
        """
        # Explizite Location
        if force_location:
            return self._create_assignment(task, force_location, session_id)

        # Server-Only Tasks
        if task.task_type in self.SERVER_ONLY_TASKS:
            return TaskAssignment(
                task=task,
                location=TaskLocation.SERVER,
                reason=f"Task '{task.task_type}' requires server resources",
            )

        # Client-Preferred Tasks
        if task.task_type in self.CLIENT_PREFERRED_TASKS:
            client_info = self._client_sessions.get(session_id)
            if client_info and client_info.capability.value <= ClientCapability.WASM_SIMD.value:
                return self._create_client_assignment(task, client_info)

        # Hybrid: Server überlastet -> Client
        if self._server_load > 0.8 and session_id in self._client_sessions:
            client_info = self._client_sessions[session_id]
            if self._can_client_handle(task, client_info):
                return self._create_client_assignment(task, client_info)

        # Default: Server
        return TaskAssignment(
            task=task,
            location=TaskLocation.SERVER,
            reason="Default server execution",
        )

    def _can_client_handle(self, task: ComputeTask, client_info: ClientGPUInfo) -> bool:
        """Prüft ob Client den Task handlen kann"""
        if task.task_type == "embedding":
            return client_info.capability.value <= ClientCapability.WASM_SIMD.value
        if task.task_type == "sentiment_analysis":
            return client_info.capability.value <= ClientCapability.WEBGPU.value
        return False

    def _create_client_assignment(
        self,
        task: ComputeTask,
        client_info: ClientGPUInfo
    ) -> TaskAssignment:
        """Erstellt Client-seitige Task-Zuweisung"""
        # Finde passendes Client-Model
        client_model = None
        instructions = {}

        if task.task_type == "embedding":
            model_config = self.CLIENT_MODELS.get("embedding_small", {})
            client_model = model_config.get("transformers_js")
            instructions = {
                "pipeline": "feature-extraction",
                "model": client_model,
                "options": {"pooling": "mean", "normalize": True},
            }
        elif task.task_type == "sentiment_analysis":
            model_config = self.CLIENT_MODELS.get("sentiment", {})
            client_model = model_config.get("transformers_js")
            instructions = {
                "pipeline": "sentiment-analysis",
                "model": client_model,
            }

        return TaskAssignment(
            task=task,
            location=TaskLocation.CLIENT,
            client_model=client_model,
            client_instructions=instructions,
            reason=f"Client WebGPU execution ({client_info.capability.name})",
        )

    def _create_assignment(
        self,
        task: ComputeTask,
        location: TaskLocation,
        session_id: Optional[str]
    ) -> TaskAssignment:
        """Erstellt Task-Zuweisung für explizite Location"""
        if location == TaskLocation.CLIENT and session_id:
            client_info = self._client_sessions.get(session_id)
            if client_info:
                return self._create_client_assignment(task, client_info)

        return TaskAssignment(
            task=task,
            location=TaskLocation.SERVER,
            reason=f"Forced {location.value} execution",
        )

    def update_server_load(self, load: float):
        """Aktualisiert Server-Last (0.0-1.0)"""
        self._server_load = max(0.0, min(1.0, load))

    def get_stats(self) -> Dict[str, Any]:
        """Gibt Statistiken zurück"""
        return {
            "server_load": self._server_load,
            "connected_clients": len(self._client_sessions),
            "clients": {
                sid: {
                    "capability": info.capability.name,
                    "gpu": info.gpu_name,
                }
                for sid, info in self._client_sessions.items()
            },
        }


# === Pydantic Models für API ===

class ClientGPUInfoRequest(BaseModel):
    """Request für Client GPU Registration"""
    capability: str = "JS_ONLY"
    gpu_vendor: str = ""
    gpu_name: str = ""
    max_buffer_size: int = 0
    max_texture_size: int = 0
    supports_f16: bool = False
    supports_storage_buffers: bool = False
    estimated_tflops: float = 0.0


class ComputeTaskRequest(BaseModel):
    """Request für Compute Task"""
    task_type: str
    input_data: Any
    model_id: Optional[str] = None
    priority: int = 5
    params: Dict[str, Any] = {}


# === Singleton ===
hybrid_router = HybridComputeRouter()


def get_hybrid_router() -> HybridComputeRouter:
    return hybrid_router
