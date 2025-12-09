"""
Hardware Acceleration Service - Universal Auto-Detection
=========================================================

Automatische Erkennung und Nutzung von:
- NVIDIA CUDA (cuDNN, TensorRT)
- AMD ROCm (HIP, MIOpen)
- Intel oneAPI (oneDNN, OpenVINO)
- CPU Optimierungen (AVX2, AVX-512, OpenBLAS, MKL)

Beim Start wird die beste verfügbare Hardware erkannt und konfiguriert.
"""

import os
import logging
import platform
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger("ailinux.hardware")


class AcceleratorType(Enum):
    """Verfügbare Beschleuniger-Typen"""
    CUDA = auto()       # NVIDIA CUDA
    ROCM = auto()       # AMD ROCm/HIP
    ONEAPI = auto()     # Intel oneAPI
    METAL = auto()      # Apple Metal (macOS)
    VULKAN = auto()     # Vulkan Compute
    OPENCL = auto()     # OpenCL
    CPU_AVX512 = auto() # CPU mit AVX-512
    CPU_AVX2 = auto()   # CPU mit AVX2
    CPU_SSE = auto()    # CPU mit SSE4.2
    CPU_BASIC = auto()  # Basis CPU


@dataclass
class GPUDevice:
    """GPU-Geräteinformationen"""
    index: int
    name: str
    memory_total: int  # in MB
    memory_free: int   # in MB
    compute_capability: str = ""
    driver_version: str = ""
    accelerator: AcceleratorType = AcceleratorType.CPU_BASIC


@dataclass
class CPUFeatures:
    """CPU-Feature-Flags"""
    avx512: bool = False
    avx2: bool = False
    avx: bool = False
    fma: bool = False
    sse42: bool = False
    sse41: bool = False
    aes: bool = False
    cores: int = 1
    threads: int = 1
    model: str = "Unknown"

    @property
    def best_simd(self) -> AcceleratorType:
        if self.avx512:
            return AcceleratorType.CPU_AVX512
        elif self.avx2:
            return AcceleratorType.CPU_AVX2
        elif self.sse42:
            return AcceleratorType.CPU_SSE
        return AcceleratorType.CPU_BASIC


@dataclass
class HardwareConfig:
    """Komplette Hardware-Konfiguration"""
    primary_accelerator: AcceleratorType = AcceleratorType.CPU_BASIC
    available_accelerators: List[AcceleratorType] = field(default_factory=list)
    gpus: List[GPUDevice] = field(default_factory=list)
    cpu: CPUFeatures = field(default_factory=CPUFeatures)
    total_gpu_memory: int = 0  # MB
    total_system_memory: int = 0  # MB
    recommended_batch_size: int = 1
    recommended_threads: int = 4
    env_vars: Dict[str, str] = field(default_factory=dict)


class HardwareDetector:
    """Hardware-Erkennung und Konfiguration"""

    def __init__(self):
        self.config = HardwareConfig()
        self._detected = False

    def detect_all(self) -> HardwareConfig:
        """Erkennt alle verfügbare Hardware"""
        if self._detected:
            return self.config

        logger.info("=== Hardware Auto-Detection gestartet ===")

        # CPU Features erkennen
        self._detect_cpu()

        # GPU Detection in Reihenfolge der Präferenz
        cuda_found = self._detect_cuda()
        rocm_found = self._detect_rocm()
        oneapi_found = self._detect_oneapi()

        # System Memory
        self._detect_system_memory()

        # Primären Accelerator bestimmen
        self._determine_primary_accelerator()

        # Optimale Konfiguration berechnen
        self._calculate_optimal_config()

        # Environment Variables setzen
        self._setup_environment()

        self._detected = True
        self._log_config()

        return self.config

    def _detect_cpu(self) -> None:
        """CPU-Features erkennen"""
        try:
            # Linux: /proc/cpuinfo parsen
            if Path("/proc/cpuinfo").exists():
                cpuinfo = Path("/proc/cpuinfo").read_text()

                # Model Name
                for line in cpuinfo.split("\n"):
                    if "model name" in line:
                        self.config.cpu.model = line.split(":")[1].strip()
                        break

                # Flags
                for line in cpuinfo.split("\n"):
                    if "flags" in line:
                        flags = line.split(":")[1].lower()
                        self.config.cpu.avx512 = "avx512" in flags or "avx512f" in flags
                        self.config.cpu.avx2 = "avx2" in flags
                        self.config.cpu.avx = "avx " in flags or flags.endswith("avx")
                        self.config.cpu.fma = "fma" in flags
                        self.config.cpu.sse42 = "sse4_2" in flags
                        self.config.cpu.sse41 = "sse4_1" in flags
                        self.config.cpu.aes = "aes" in flags
                        break

                # Cores/Threads
                self.config.cpu.cores = cpuinfo.count("processor")
                self.config.cpu.threads = self.config.cpu.cores  # Vereinfacht

            # macOS
            elif platform.system() == "Darwin":
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True, text=True
                )
                self.config.cpu.model = result.stdout.strip()

                result = subprocess.run(
                    ["sysctl", "-n", "hw.ncpu"],
                    capture_output=True, text=True
                )
                self.config.cpu.cores = int(result.stdout.strip())
                self.config.cpu.threads = self.config.cpu.cores

                # Apple Silicon hat keine x86 SIMD
                if "Apple" in self.config.cpu.model:
                    self.config.cpu.avx2 = False
                    self.config.cpu.avx = False

            # Füge CPU-Accelerator hinzu
            self.config.available_accelerators.append(self.config.cpu.best_simd)

            logger.info(f"CPU: {self.config.cpu.model}")
            logger.info(f"  Cores: {self.config.cpu.cores}, AVX2: {self.config.cpu.avx2}, AVX-512: {self.config.cpu.avx512}")

        except Exception as e:
            logger.warning(f"CPU Detection Fehler: {e}")
            self.config.available_accelerators.append(AcceleratorType.CPU_BASIC)

    def _detect_cuda(self) -> bool:
        """NVIDIA CUDA erkennen"""
        try:
            # nvidia-smi verfügbar?
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.free,driver_version,compute_cap",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode != 0:
                return False

            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 5:
                    gpu = GPUDevice(
                        index=int(parts[0]),
                        name=parts[1],
                        memory_total=int(parts[2]),
                        memory_free=int(parts[3]),
                        driver_version=parts[4],
                        compute_capability=parts[5] if len(parts) > 5 else "",
                        accelerator=AcceleratorType.CUDA
                    )
                    self.config.gpus.append(gpu)
                    self.config.total_gpu_memory += gpu.memory_total

            if self.config.gpus:
                self.config.available_accelerators.append(AcceleratorType.CUDA)
                logger.info(f"CUDA: {len(self.config.gpus)} GPU(s) erkannt")
                for gpu in self.config.gpus:
                    logger.info(f"  [{gpu.index}] {gpu.name} - {gpu.memory_total}MB VRAM")
                return True

        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug(f"CUDA Detection: {e}")

        return False

    def _detect_rocm(self) -> bool:
        """AMD ROCm erkennen"""
        try:
            # rocminfo verfügbar?
            result = subprocess.run(
                ["rocminfo"],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                return False

            # Parse rocminfo output
            gpu_count = 0
            current_gpu = None

            for line in result.stdout.split("\n"):
                if "Name:" in line and "gfx" in line.lower():
                    # AMD GPU gefunden
                    name = line.split(":")[-1].strip()
                    current_gpu = GPUDevice(
                        index=gpu_count,
                        name=name,
                        memory_total=0,
                        memory_free=0,
                        accelerator=AcceleratorType.ROCM
                    )
                    gpu_count += 1
                elif "Size:" in line and current_gpu and "bytes" in line.lower():
                    # Memory Size
                    try:
                        size_str = line.split(":")[-1].strip().split()[0]
                        current_gpu.memory_total = int(size_str) // (1024 * 1024)
                        current_gpu.memory_free = current_gpu.memory_total
                        self.config.gpus.append(current_gpu)
                        self.config.total_gpu_memory += current_gpu.memory_total
                        current_gpu = None
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Could not parse GPU memory size: {e}")

            if gpu_count > 0:
                self.config.available_accelerators.append(AcceleratorType.ROCM)
                logger.info(f"ROCm: {gpu_count} GPU(s) erkannt")
                return True

        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug(f"ROCm Detection: {e}")

        return False

    def _detect_oneapi(self) -> bool:
        """Intel oneAPI erkennen"""
        try:
            # Check for Intel GPU via sycl-ls or clinfo
            oneapi_root = os.environ.get("ONEAPI_ROOT", "/opt/intel/oneapi")

            if Path(oneapi_root).exists():
                self.config.available_accelerators.append(AcceleratorType.ONEAPI)
                logger.info("Intel oneAPI: Installation erkannt")
                return True

            # Check for Intel GPU via OpenCL
            result = subprocess.run(
                ["clinfo", "-l"],
                capture_output=True, text=True, timeout=5
            )

            if "Intel" in result.stdout:
                self.config.available_accelerators.append(AcceleratorType.OPENCL)
                logger.info("Intel OpenCL: GPU erkannt")
                return True

        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug(f"oneAPI Detection: {e}")

        return False

    def _detect_system_memory(self) -> None:
        """System-Speicher erkennen"""
        try:
            if Path("/proc/meminfo").exists():
                meminfo = Path("/proc/meminfo").read_text()
                for line in meminfo.split("\n"):
                    if "MemTotal:" in line:
                        # Format: MemTotal: 12345678 kB
                        kb = int(line.split()[1])
                        self.config.total_system_memory = kb // 1024  # MB
                        break

            logger.info(f"System RAM: {self.config.total_system_memory} MB")

        except Exception as e:
            logger.warning(f"Memory Detection Fehler: {e}")

    def _determine_primary_accelerator(self) -> None:
        """Bestimmt den primären Beschleuniger"""
        priority = [
            AcceleratorType.CUDA,
            AcceleratorType.ROCM,
            AcceleratorType.ONEAPI,
            AcceleratorType.METAL,
            AcceleratorType.CPU_AVX512,
            AcceleratorType.CPU_AVX2,
            AcceleratorType.CPU_SSE,
            AcceleratorType.CPU_BASIC,
        ]

        for accel in priority:
            if accel in self.config.available_accelerators:
                self.config.primary_accelerator = accel
                break

        logger.info(f"Primärer Accelerator: {self.config.primary_accelerator.name}")

    def _calculate_optimal_config(self) -> None:
        """Berechnet optimale Konfiguration"""
        # Batch Size basierend auf GPU Memory
        if self.config.total_gpu_memory > 0:
            # Grobe Heuristik: 1GB VRAM = Batch Size 8
            self.config.recommended_batch_size = min(
                64, max(1, self.config.total_gpu_memory // 1024 * 8)
            )
        else:
            # CPU: konservativer
            self.config.recommended_batch_size = min(8, self.config.cpu.cores)

        # Thread Count
        self.config.recommended_threads = max(4, self.config.cpu.cores - 2)

    def _setup_environment(self) -> None:
        """Setzt optimale Environment Variables"""
        env = self.config.env_vars

        # === CPU Optimierungen ===
        env["OMP_NUM_THREADS"] = str(self.config.recommended_threads)
        env["MKL_NUM_THREADS"] = str(self.config.recommended_threads)
        env["OPENBLAS_NUM_THREADS"] = str(self.config.recommended_threads)
        env["VECLIB_MAXIMUM_THREADS"] = str(self.config.recommended_threads)
        env["NUMEXPR_NUM_THREADS"] = str(self.config.recommended_threads)

        # ONNX Runtime
        env["ORT_DISABLE_ALL"] = "0"

        # === GPU-spezifische Settings ===
        if AcceleratorType.CUDA in self.config.available_accelerators:
            # CUDA Optimierungen
            env["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
            env["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"
            env["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"

            # cuDNN
            env["TF_CUDNN_USE_AUTOTUNE"] = "1"
            env["CUDNN_FRONTEND_LOG_FILE"] = "/dev/null"

        if AcceleratorType.ROCM in self.config.available_accelerators:
            # ROCm/HIP Optimierungen
            env["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"  # Fallback für neuere GPUs
            env["HIP_VISIBLE_DEVICES"] = "0"
            env["ROCM_PATH"] = "/opt/rocm"
            env["HSA_ENABLE_SDMA"] = "0"  # Stabilität

        if AcceleratorType.ONEAPI in self.config.available_accelerators:
            # Intel oneAPI
            env["SYCL_DEVICE_FILTER"] = "level_zero:gpu"
            env["EnableImplicitScaling"] = "1"

        # === Allgemeine Optimierungen ===
        env["TOKENIZERS_PARALLELISM"] = "true"
        env["TRANSFORMERS_OFFLINE"] = "0"

        # AVX-512 spezifisch
        if self.config.cpu.avx512:
            env["DNNL_MAX_CPU_ISA"] = "AVX512_CORE_AMX"
        elif self.config.cpu.avx2:
            env["DNNL_MAX_CPU_ISA"] = "AVX2"

        # Environment setzen
        for key, value in env.items():
            os.environ[key] = value

    def _log_config(self) -> None:
        """Loggt die finale Konfiguration"""
        logger.info("=== Hardware-Konfiguration ===")
        logger.info(f"  Primary: {self.config.primary_accelerator.name}")
        logger.info(f"  Available: {[a.name for a in self.config.available_accelerators]}")
        logger.info(f"  GPUs: {len(self.config.gpus)}")
        logger.info(f"  GPU VRAM: {self.config.total_gpu_memory} MB")
        logger.info(f"  System RAM: {self.config.total_system_memory} MB")
        logger.info(f"  Recommended Batch: {self.config.recommended_batch_size}")
        logger.info(f"  Recommended Threads: {self.config.recommended_threads}")
        logger.info("================================")

    def get_pytorch_device(self) -> str:
        """Gibt das optimale PyTorch Device zurück"""
        if AcceleratorType.CUDA in self.config.available_accelerators:
            return "cuda"
        elif AcceleratorType.ROCM in self.config.available_accelerators:
            return "cuda"  # PyTorch ROCm nutzt auch "cuda"
        elif AcceleratorType.METAL in self.config.available_accelerators:
            return "mps"
        return "cpu"

    def get_onnx_providers(self) -> List[str]:
        """Gibt optimale ONNX Runtime Providers zurück"""
        providers = []

        if AcceleratorType.CUDA in self.config.available_accelerators:
            providers.extend(["CUDAExecutionProvider", "TensorrtExecutionProvider"])

        if AcceleratorType.ROCM in self.config.available_accelerators:
            providers.append("ROCMExecutionProvider")

        if AcceleratorType.ONEAPI in self.config.available_accelerators:
            providers.append("DmlExecutionProvider")

        if AcceleratorType.OPENCL in self.config.available_accelerators:
            providers.append("OpenVINOExecutionProvider")

        # CPU Provider immer als Fallback
        providers.append("CPUExecutionProvider")

        return providers

    def get_llama_cpp_args(self) -> Dict[str, Any]:
        """Gibt optimale llama.cpp Argumente zurück"""
        args = {
            "n_threads": self.config.recommended_threads,
            "n_batch": self.config.recommended_batch_size * 512,
        }

        if AcceleratorType.CUDA in self.config.available_accelerators:
            args["n_gpu_layers"] = -1  # Alle Layer auf GPU
            args["main_gpu"] = 0
            args["tensor_split"] = None

        elif AcceleratorType.ROCM in self.config.available_accelerators:
            args["n_gpu_layers"] = -1

        return args

    def to_dict(self) -> Dict[str, Any]:
        """Exportiert Konfiguration als Dictionary"""
        return {
            "primary_accelerator": self.config.primary_accelerator.name,
            "available_accelerators": [a.name for a in self.config.available_accelerators],
            "gpus": [
                {
                    "index": g.index,
                    "name": g.name,
                    "memory_total_mb": g.memory_total,
                    "memory_free_mb": g.memory_free,
                    "type": g.accelerator.name,
                }
                for g in self.config.gpus
            ],
            "cpu": {
                "model": self.config.cpu.model,
                "cores": self.config.cpu.cores,
                "avx2": self.config.cpu.avx2,
                "avx512": self.config.cpu.avx512,
                "fma": self.config.cpu.fma,
            },
            "total_gpu_memory_mb": self.config.total_gpu_memory,
            "total_system_memory_mb": self.config.total_system_memory,
            "recommended_batch_size": self.config.recommended_batch_size,
            "recommended_threads": self.config.recommended_threads,
            "pytorch_device": self.get_pytorch_device(),
            "onnx_providers": self.get_onnx_providers(),
        }


# === Singleton Instance ===
_detector: Optional[HardwareDetector] = None


def get_hardware_config() -> HardwareConfig:
    """Gibt die Hardware-Konfiguration zurück (cached)"""
    global _detector
    if _detector is None:
        _detector = HardwareDetector()
        _detector.detect_all()
    return _detector.config


def get_hardware_detector() -> HardwareDetector:
    """Gibt den Hardware-Detector zurück"""
    global _detector
    if _detector is None:
        _detector = HardwareDetector()
        _detector.detect_all()
    return _detector


def get_device() -> str:
    """Shortcut für PyTorch Device"""
    return get_hardware_detector().get_pytorch_device()


def get_threads() -> int:
    """Shortcut für optimale Thread-Anzahl"""
    return get_hardware_config().recommended_threads


def get_batch_size() -> int:
    """Shortcut für optimale Batch-Size"""
    return get_hardware_config().recommended_batch_size


# === Startup Detection ===
def init_hardware_acceleration() -> Dict[str, Any]:
    """
    Initialisiert Hardware-Beschleunigung beim Server-Start.
    Sollte in main.py während lifespan aufgerufen werden.
    """
    detector = get_hardware_detector()
    config = detector.to_dict()

    logger.info("Hardware Acceleration initialisiert")
    return config
