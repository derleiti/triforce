"""
Compute Backend Abstraction Layer
=================================

Einheitliche API für GPU/CPU-beschleunigte Operationen.
Unterstützt automatisches Fallback zwischen:
- CUDA (NVIDIA)
- ROCm (AMD)
- oneAPI (Intel)
- CPU (OpenBLAS, MKL, ONNX)

Verwendung:
    from app.services.compute_backend import compute

    # Automatisch bestes Backend
    result = await compute.inference(model, input_data)

    # Embeddings mit GPU-Beschleunigung
    embeddings = await compute.embed(texts)

    # Matrix-Operationen
    result = compute.matmul(a, b)
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum, auto

from .hardware_accel import (
    get_hardware_config,
    get_hardware_detector,
)

if TYPE_CHECKING:
    import numpy as np
    import torch

logger = logging.getLogger("ailinux.compute")


class ComputeBackendType(Enum):
    """Backend-Typen für Compute-Operationen"""
    PYTORCH_CUDA = auto()
    PYTORCH_ROCM = auto()
    PYTORCH_CPU = auto()
    ONNX_CUDA = auto()
    ONNX_ROCM = auto()
    ONNX_CPU = auto()
    NUMPY = auto()
    LLAMA_CPP = auto()


@dataclass
class ComputeResult:
    """Ergebnis einer Compute-Operation"""
    data: Any
    backend: ComputeBackendType
    device: str
    elapsed_ms: float
    memory_used_mb: float = 0.0


class ComputeBackend(ABC):
    """Abstrakte Basisklasse für Compute-Backends"""

    @abstractmethod
    def is_available(self) -> bool:
        """Prüft ob das Backend verfügbar ist"""
        raise NotImplementedError("Subclass must implement is_available()")

    @abstractmethod
    async def inference(
        self,
        model: Any,
        inputs: Any,
        **kwargs
    ) -> ComputeResult:
        """Führt Inferenz durch"""
        raise NotImplementedError("Subclass must implement inference()")

    @abstractmethod
    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None,
        **kwargs
    ) -> ComputeResult:
        """Erstellt Embeddings"""
        raise NotImplementedError("Subclass must implement embed()")

    @abstractmethod
    def to_device(self, data: Any) -> Any:
        """Verschiebt Daten auf das Compute-Device"""
        raise NotImplementedError("Subclass must implement to_device()")

    @abstractmethod
    def to_cpu(self, data: Any) -> Any:
        """Verschiebt Daten zurück auf CPU"""
        raise NotImplementedError("Subclass must implement to_cpu()")


class PyTorchBackend(ComputeBackend):
    """PyTorch-basiertes Compute-Backend (CUDA/ROCm/CPU)"""

    def __init__(self, device: str = "auto"):
        self._device = device
        self._torch = None
        self._actual_device = None

    def _lazy_init(self):
        """Lazy-Load PyTorch"""
        if self._torch is not None:
            return

        try:
            import torch
            self._torch = torch

            if self._device == "auto":
                detector = get_hardware_detector()
                self._actual_device = detector.get_pytorch_device()
            else:
                self._actual_device = self._device

            logger.info(f"PyTorch Backend: device={self._actual_device}")

        except ImportError:
            logger.warning("PyTorch nicht installiert")
            self._torch = None

    def is_available(self) -> bool:
        self._lazy_init()
        return self._torch is not None

    @property
    def device(self) -> str:
        self._lazy_init()
        return self._actual_device or "cpu"

    async def inference(
        self,
        model: Any,
        inputs: Any,
        **kwargs
    ) -> ComputeResult:
        self._lazy_init()
        if not self._torch:
            raise RuntimeError("PyTorch nicht verfügbar")

        import time
        start = time.perf_counter()

        # Model und Input auf Device verschieben
        model = model.to(self.device)
        if hasattr(inputs, 'to'):
            inputs = inputs.to(self.device)

        # Inferenz
        with self._torch.no_grad():
            if kwargs.get("amp", True) and self.device != "cpu":
                with self._torch.cuda.amp.autocast():
                    output = model(inputs)
            else:
                output = model(inputs)

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Memory Stats
        memory_mb = 0.0
        if self.device.startswith("cuda"):
            memory_mb = self._torch.cuda.memory_allocated() / (1024 * 1024)

        return ComputeResult(
            data=output,
            backend=ComputeBackendType.PYTORCH_CUDA if "cuda" in self.device else ComputeBackendType.PYTORCH_CPU,
            device=self.device,
            elapsed_ms=elapsed_ms,
            memory_used_mb=memory_mb,
        )

    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None,
        **kwargs
    ) -> ComputeResult:
        """Erstellt Embeddings mit SentenceTransformers oder HuggingFace"""
        self._lazy_init()
        if not self._torch:
            raise RuntimeError("PyTorch nicht verfügbar")

        import time
        start = time.perf_counter()

        try:
            from sentence_transformers import SentenceTransformer

            model_name = model or "sentence-transformers/all-MiniLM-L6-v2"
            encoder = SentenceTransformer(model_name, device=self.device)
            embeddings = encoder.encode(
                texts,
                convert_to_tensor=True,
                show_progress_bar=False,
                **kwargs
            )

        except ImportError:
            # Fallback zu transformers
            from transformers import AutoTokenizer, AutoModel

            model_name = model or "sentence-transformers/all-MiniLM-L6-v2"
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            encoder = AutoModel.from_pretrained(model_name).to(self.device)

            inputs = tokenizer(
                texts,
                padding=True,
                truncation=True,
                return_tensors="pt"
            ).to(self.device)

            with self._torch.no_grad():
                outputs = encoder(**inputs)
                embeddings = outputs.last_hidden_state.mean(dim=1)

        elapsed_ms = (time.perf_counter() - start) * 1000

        return ComputeResult(
            data=embeddings,
            backend=ComputeBackendType.PYTORCH_CUDA if "cuda" in self.device else ComputeBackendType.PYTORCH_CPU,
            device=self.device,
            elapsed_ms=elapsed_ms,
        )

    def to_device(self, data: Any) -> Any:
        self._lazy_init()
        if self._torch and hasattr(data, 'to'):
            return data.to(self.device)
        return data

    def to_cpu(self, data: Any) -> Any:
        if hasattr(data, 'cpu'):
            return data.cpu()
        return data


class ONNXBackend(ComputeBackend):
    """ONNX Runtime Backend (optimiert für Inferenz)"""

    def __init__(self):
        self._ort = None
        self._providers = None
        self._sessions: Dict[str, Any] = {}

    def _lazy_init(self):
        if self._ort is not None:
            return

        try:
            import onnxruntime as ort
            self._ort = ort

            detector = get_hardware_detector()
            self._providers = detector.get_onnx_providers()

            logger.info(f"ONNX Runtime: providers={self._providers}")

        except ImportError:
            logger.warning("ONNX Runtime nicht installiert")
            self._ort = None

    def is_available(self) -> bool:
        self._lazy_init()
        return self._ort is not None

    def _get_session(self, model_path: str) -> Any:
        """Cached ONNX Session"""
        if model_path not in self._sessions:
            self._sessions[model_path] = self._ort.InferenceSession(
                model_path,
                providers=self._providers
            )
        return self._sessions[model_path]

    async def inference(
        self,
        model: Any,
        inputs: Any,
        **kwargs
    ) -> ComputeResult:
        self._lazy_init()
        if not self._ort:
            raise RuntimeError("ONNX Runtime nicht verfügbar")

        import time
        import numpy as np
        start = time.perf_counter()

        # Model kann Pfad oder Session sein
        if isinstance(model, str):
            session = self._get_session(model)
        else:
            session = model

        # Input vorbereiten
        if isinstance(inputs, dict):
            ort_inputs = inputs
        else:
            input_name = session.get_inputs()[0].name
            if hasattr(inputs, 'numpy'):
                inputs = inputs.numpy()
            ort_inputs = {input_name: inputs}

        # Inferenz
        output = session.run(None, ort_inputs)

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Backend-Typ bestimmen
        backend_type = ComputeBackendType.ONNX_CPU
        if self._providers and "CUDAExecutionProvider" in self._providers:
            backend_type = ComputeBackendType.ONNX_CUDA
        elif self._providers and "ROCMExecutionProvider" in self._providers:
            backend_type = ComputeBackendType.ONNX_ROCM

        return ComputeResult(
            data=output,
            backend=backend_type,
            device="onnx",
            elapsed_ms=elapsed_ms,
        )

    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None,
        **kwargs
    ) -> ComputeResult:
        """ONNX-basierte Embeddings (falls ONNX-Modell vorhanden)"""
        # Fallback zu PyTorch für Embeddings
        pytorch_backend = PyTorchBackend()
        return await pytorch_backend.embed(texts, model, **kwargs)

    def to_device(self, data: Any) -> Any:
        # ONNX handled device intern
        return data

    def to_cpu(self, data: Any) -> Any:
        import numpy as np
        if hasattr(data, 'numpy'):
            return data.numpy()
        return data


class LlamaCppBackend(ComputeBackend):
    """llama.cpp Backend für LLM-Inferenz"""

    def __init__(self):
        self._llama = None
        self._models: Dict[str, Any] = {}

    def _lazy_init(self):
        if self._llama is not None:
            return

        try:
            from llama_cpp import Llama
            self._llama = Llama

            detector = get_hardware_detector()
            self._default_args = detector.get_llama_cpp_args()

            logger.info(f"llama.cpp: n_gpu_layers={self._default_args.get('n_gpu_layers', 0)}")

        except ImportError:
            logger.warning("llama-cpp-python nicht installiert")
            self._llama = None

    def is_available(self) -> bool:
        self._lazy_init()
        return self._llama is not None

    def load_model(self, model_path: str, **kwargs) -> Any:
        """Lädt ein GGUF-Modell"""
        self._lazy_init()
        if not self._llama:
            raise RuntimeError("llama.cpp nicht verfügbar")

        if model_path not in self._models:
            args = {**self._default_args, **kwargs}
            self._models[model_path] = self._llama(model_path, **args)

        return self._models[model_path]

    async def inference(
        self,
        model: Any,
        inputs: Any,
        **kwargs
    ) -> ComputeResult:
        self._lazy_init()
        if not self._llama:
            raise RuntimeError("llama.cpp nicht verfügbar")

        import time
        start = time.perf_counter()

        # Model laden falls Pfad
        if isinstance(model, str):
            model = self.load_model(model)

        # Generierung
        prompt = inputs if isinstance(inputs, str) else str(inputs)
        output = model(
            prompt,
            max_tokens=kwargs.get("max_tokens", 512),
            temperature=kwargs.get("temperature", 0.7),
            top_p=kwargs.get("top_p", 0.95),
            echo=kwargs.get("echo", False),
        )

        elapsed_ms = (time.perf_counter() - start) * 1000

        return ComputeResult(
            data=output,
            backend=ComputeBackendType.LLAMA_CPP,
            device="llama.cpp",
            elapsed_ms=elapsed_ms,
        )

    async def embed(
        self,
        texts: List[str],
        model: Optional[str] = None,
        **kwargs
    ) -> ComputeResult:
        """Embeddings mit llama.cpp (falls Embedding-Modell)"""
        self._lazy_init()
        if not self._llama:
            raise RuntimeError("llama.cpp nicht verfügbar")

        import time
        start = time.perf_counter()

        if model:
            llm = self.load_model(model, embedding=True)
        else:
            raise ValueError("Model-Pfad für Embeddings erforderlich")

        embeddings = [llm.embed(text) for text in texts]

        elapsed_ms = (time.perf_counter() - start) * 1000

        return ComputeResult(
            data=embeddings,
            backend=ComputeBackendType.LLAMA_CPP,
            device="llama.cpp",
            elapsed_ms=elapsed_ms,
        )

    def to_device(self, data: Any) -> Any:
        return data

    def to_cpu(self, data: Any) -> Any:
        return data


class ComputeManager:
    """
    Hauptklasse für Compute-Operationen.
    Wählt automatisch das beste verfügbare Backend.
    """

    def __init__(self):
        self._pytorch: Optional[PyTorchBackend] = None
        self._onnx: Optional[ONNXBackend] = None
        self._llama: Optional[LlamaCppBackend] = None
        self._initialized = False

    def _init_backends(self):
        """Initialisiert verfügbare Backends"""
        if self._initialized:
            return

        self._pytorch = PyTorchBackend()
        self._onnx = ONNXBackend()
        self._llama = LlamaCppBackend()

        self._initialized = True

        # Log verfügbare Backends
        available = []
        if self._pytorch.is_available():
            available.append(f"PyTorch({self._pytorch.device})")
        if self._onnx.is_available():
            available.append("ONNX")
        if self._llama.is_available():
            available.append("llama.cpp")

        logger.info(f"Compute Backends: {', '.join(available) or 'None'}")

    @property
    def device(self) -> str:
        """Aktuelles primäres Compute-Device"""
        self._init_backends()
        if self._pytorch and self._pytorch.is_available():
            return self._pytorch.device
        return "cpu"

    @property
    def pytorch(self) -> PyTorchBackend:
        """PyTorch Backend"""
        self._init_backends()
        return self._pytorch

    @property
    def onnx(self) -> ONNXBackend:
        """ONNX Runtime Backend"""
        self._init_backends()
        return self._onnx

    @property
    def llama(self) -> LlamaCppBackend:
        """llama.cpp Backend"""
        self._init_backends()
        return self._llama

    async def inference(
        self,
        model: Any,
        inputs: Any,
        backend: Optional[str] = None,
        **kwargs
    ) -> ComputeResult:
        """
        Führt Inferenz mit dem besten verfügbaren Backend durch.

        Args:
            model: Modell (Pfad, PyTorch-Modell, oder ONNX-Session)
            inputs: Input-Daten
            backend: Optional erzwungenes Backend ("pytorch", "onnx", "llama")
        """
        self._init_backends()

        # Explizites Backend
        if backend == "pytorch":
            return await self._pytorch.inference(model, inputs, **kwargs)
        elif backend == "onnx":
            return await self._onnx.inference(model, inputs, **kwargs)
        elif backend == "llama":
            return await self._llama.inference(model, inputs, **kwargs)

        # Auto-Auswahl basierend auf Modell-Typ
        if isinstance(model, str):
            if model.endswith(".gguf"):
                return await self._llama.inference(model, inputs, **kwargs)
            elif model.endswith(".onnx"):
                return await self._onnx.inference(model, inputs, **kwargs)

        # Default: PyTorch
        if self._pytorch.is_available():
            return await self._pytorch.inference(model, inputs, **kwargs)

        raise RuntimeError("Kein Compute-Backend verfügbar")

    async def embed(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs
    ) -> ComputeResult:
        """
        Erstellt Embeddings mit dem besten verfügbaren Backend.
        """
        self._init_backends()

        if isinstance(texts, str):
            texts = [texts]

        # PyTorch für Standard-Embeddings
        if self._pytorch.is_available():
            return await self._pytorch.embed(texts, model, **kwargs)

        raise RuntimeError("Kein Embedding-Backend verfügbar")

    def to_device(self, data: Any) -> Any:
        """Verschiebt Daten auf das aktive Compute-Device"""
        self._init_backends()
        if self._pytorch.is_available():
            return self._pytorch.to_device(data)
        return data

    def to_cpu(self, data: Any) -> Any:
        """Verschiebt Daten zurück auf CPU"""
        self._init_backends()
        if self._pytorch.is_available():
            return self._pytorch.to_cpu(data)
        return data

    def get_status(self) -> Dict[str, Any]:
        """Gibt Status aller Backends zurück"""
        self._init_backends()

        hw_config = get_hardware_config()

        return {
            "primary_device": self.device,
            "backends": {
                "pytorch": {
                    "available": self._pytorch.is_available() if self._pytorch else False,
                    "device": self._pytorch.device if self._pytorch and self._pytorch.is_available() else None,
                },
                "onnx": {
                    "available": self._onnx.is_available() if self._onnx else False,
                    "providers": self._onnx._providers if self._onnx and self._onnx.is_available() else [],
                },
                "llama_cpp": {
                    "available": self._llama.is_available() if self._llama else False,
                },
            },
            "hardware": {
                "accelerator": hw_config.primary_accelerator.name,
                "gpu_count": len(hw_config.gpus),
                "gpu_memory_mb": hw_config.total_gpu_memory,
                "recommended_threads": hw_config.recommended_threads,
                "recommended_batch_size": hw_config.recommended_batch_size,
            },
        }


# === Singleton Instance ===
compute = ComputeManager()


# === Convenience Functions ===
def get_device() -> str:
    """Gibt das aktive Compute-Device zurück"""
    return compute.device


async def inference(model: Any, inputs: Any, **kwargs) -> ComputeResult:
    """Shortcut für Inferenz"""
    return await compute.inference(model, inputs, **kwargs)


async def embed(texts: Union[str, List[str]], **kwargs) -> ComputeResult:
    """Shortcut für Embeddings"""
    return await compute.embed(texts, **kwargs)
