"""
Hardware Acceleration Service - Universal Auto-Detection v2.0
=============================================================

Optimiert für:
- Intel Core Ultra (Arrow Lake) - Hybrid P/E/LP-E Core Architecture
- Intel Alder Lake / Raptor Lake Hybrid CPUs
- AMD Ryzen (Zen 4/5)
- NVIDIA CUDA (cuDNN, TensorRT)
- AMD ROCm (HIP, MIOpen)
- Intel oneAPI (oneDNN, OpenVINO)

Changelog v2.0:
- Arrow Lake Support (kein AVX-512!)
- Hybrid Core Detection (P-Cores, E-Cores, LP-E-Cores)
- Uvicorn Worker Empfehlungen
- Verbesserte Thread-Affinität für Hybrid CPUs
"""

import os
import logging
import platform
import subprocess
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger("ailinux.hardware")


class AcceleratorType(Enum):
    CUDA = auto()
    ROCM = auto()
    ONEAPI = auto()
    METAL = auto()
    VULKAN = auto()
    OPENCL = auto()
    CPU_AVX512 = auto()
    CPU_AVX2 = auto()
    CPU_SSE = auto()
    CPU_BASIC = auto()


class CPUArchitecture(Enum):
    INTEL_ARROW_LAKE = "arrow_lake"
    INTEL_METEOR_LAKE = "meteor_lake"
    INTEL_RAPTOR_LAKE = "raptor_lake"
    INTEL_ALDER_LAKE = "alder_lake"
    INTEL_LEGACY = "intel_legacy"
    AMD_ZEN5 = "zen5"
    AMD_ZEN4 = "zen4"
    AMD_ZEN3 = "zen3"
    AMD_LEGACY = "amd_legacy"
    APPLE_SILICON = "apple_silicon"
    UNKNOWN = "unknown"


@dataclass
class GPUDevice:
    index: int
    name: str
    memory_total: int
    memory_free: int
    compute_capability: str = ""
    driver_version: str = ""
    accelerator: AcceleratorType = AcceleratorType.CPU_BASIC


@dataclass
class CPUFeatures:
    avx512: bool = False
    avx2: bool = False
    avx: bool = False
    fma: bool = False
    sse42: bool = False
    sse41: bool = False
    aes: bool = False
    sha_ni: bool = False
    avx_vnni: bool = False
    cores: int = 1
    threads: int = 1
    p_cores: int = 0
    e_cores: int = 0
    lpe_cores: int = 0
    sockets: int = 1
    l3_cache_mb: int = 0
    model: str = "Unknown"
    vendor: str = "Unknown"
    family: int = 0
    model_id: int = 0
    stepping: int = 0
    architecture: CPUArchitecture = CPUArchitecture.UNKNOWN
    max_mhz: float = 0.0

    @property
    def best_simd(self) -> AcceleratorType:
        if self.avx512:
            return AcceleratorType.CPU_AVX512
        elif self.avx2:
            return AcceleratorType.CPU_AVX2
        elif self.sse42:
            return AcceleratorType.CPU_SSE
        return AcceleratorType.CPU_BASIC

    @property
    def is_hybrid(self) -> bool:
        return self.p_cores > 0 and self.e_cores > 0

    @property
    def is_arrow_lake(self) -> bool:
        return self.architecture == CPUArchitecture.INTEL_ARROW_LAKE


@dataclass
class HardwareConfig:
    primary_accelerator: AcceleratorType = AcceleratorType.CPU_BASIC
    available_accelerators: List[AcceleratorType] = field(default_factory=list)
    gpus: List[GPUDevice] = field(default_factory=list)
    cpu: CPUFeatures = field(default_factory=CPUFeatures)
    total_gpu_memory: int = 0
    total_system_memory: int = 0
    recommended_batch_size: int = 1
    recommended_threads: int = 4
    recommended_workers: int = 4
    recommended_p_core_threads: int = 0
    recommended_e_core_threads: int = 0
    env_vars: Dict[str, str] = field(default_factory=dict)


class HardwareDetector:
    """Hardware-Erkennung v2.0 - Optimiert für Intel Hybrid CPUs"""

    INTEL_ARCH_MAP = {
        (6, 198): CPUArchitecture.INTEL_ARROW_LAKE,
        (6, 170): CPUArchitecture.INTEL_METEOR_LAKE,
        (6, 183): CPUArchitecture.INTEL_RAPTOR_LAKE,
        (6, 191): CPUArchitecture.INTEL_RAPTOR_LAKE,
        (6, 151): CPUArchitecture.INTEL_ALDER_LAKE,
        (6, 154): CPUArchitecture.INTEL_ALDER_LAKE,
    }

    def __init__(self):
        self.config = HardwareConfig()
        self._detected = False

    def detect_all(self) -> HardwareConfig:
        if self._detected:
            return self.config

        logger.info("=== Hardware Auto-Detection v2.0 ===")
        self._detect_cpu()
        self._detect_hybrid_topology()
        self._detect_cuda()
        self._detect_rocm()
        self._detect_oneapi()
        self._detect_system_memory()
        self._determine_primary_accelerator()
        self._calculate_optimal_config()
        self._setup_environment()
        self._detected = True
        self._log_config()
        return self.config

    def _identify_architecture(self) -> None:
        vendor = self.config.cpu.vendor.lower()
        family = self.config.cpu.family
        model = self.config.cpu.model_id
        model_name = self.config.cpu.model.lower()

        if "intel" in vendor or "genuineintel" in vendor:
            arch = self.INTEL_ARCH_MAP.get((family, model))
            if arch:
                self.config.cpu.architecture = arch
            elif "core ultra" in model_name:
                if any(x in model_name for x in ["265", "285", "245", "225"]):
                    self.config.cpu.architecture = CPUArchitecture.INTEL_ARROW_LAKE
                else:
                    self.config.cpu.architecture = CPUArchitecture.INTEL_METEOR_LAKE
            elif "13th gen" in model_name or "14th gen" in model_name:
                self.config.cpu.architecture = CPUArchitecture.INTEL_RAPTOR_LAKE
            elif "12th gen" in model_name:
                self.config.cpu.architecture = CPUArchitecture.INTEL_ALDER_LAKE
            else:
                self.config.cpu.architecture = CPUArchitecture.INTEL_LEGACY
        elif "amd" in vendor:
            if "9000" in model_name:
                self.config.cpu.architecture = CPUArchitecture.AMD_ZEN5
            elif "7000" in model_name:
                self.config.cpu.architecture = CPUArchitecture.AMD_ZEN4
            elif "5000" in model_name:
                self.config.cpu.architecture = CPUArchitecture.AMD_ZEN3

    def _detect_cpu(self) -> None:
        try:
            if Path("/proc/cpuinfo").exists():
                cpuinfo = Path("/proc/cpuinfo").read_text()

                for line in cpuinfo.split("\n"):
                    if "model name" in line:
                        self.config.cpu.model = line.split(":")[1].strip()
                        break

                for line in cpuinfo.split("\n"):
                    if "vendor_id" in line:
                        self.config.cpu.vendor = line.split(":")[1].strip()
                        break

                for line in cpuinfo.split("\n"):
                    if line.startswith("cpu family"):
                        self.config.cpu.family = int(line.split(":")[1].strip())
                    elif line.startswith("model") and "name" not in line:
                        self.config.cpu.model_id = int(line.split(":")[1].strip())
                    elif line.startswith("stepping"):
                        self.config.cpu.stepping = int(line.split(":")[1].strip())

                self._identify_architecture()

                for line in cpuinfo.split("\n"):
                    if "flags" in line:
                        flags = line.split(":")[1].lower().split()

                        # ARROW LAKE HAT KEIN AVX-512!
                        if self.config.cpu.is_arrow_lake:
                            self.config.cpu.avx512 = False
                            logger.info("Arrow Lake: AVX-512 deaktiviert (Hardware-Limitation)")
                        else:
                            self.config.cpu.avx512 = "avx512f" in flags

                        self.config.cpu.avx2 = "avx2" in flags
                        self.config.cpu.avx = "avx" in flags
                        self.config.cpu.fma = "fma" in flags
                        self.config.cpu.sse42 = "sse4_2" in flags
                        self.config.cpu.sse41 = "sse4_1" in flags
                        self.config.cpu.aes = "aes" in flags
                        self.config.cpu.sha_ni = "sha_ni" in flags
                        self.config.cpu.avx_vnni = "avx_vnni" in flags
                        break

                self.config.cpu.cores = cpuinfo.count("processor")
                self.config.cpu.threads = self.config.cpu.cores

            self._parse_lscpu()
            self.config.available_accelerators.append(self.config.cpu.best_simd)

            logger.info(f"CPU: {self.config.cpu.model}")
            logger.info(f"  Architektur: {self.config.cpu.architecture.value}")
            logger.info(f"  Cores: {self.config.cpu.cores}, AVX2: {self.config.cpu.avx2}, AVX-512: {self.config.cpu.avx512}")
            if self.config.cpu.avx_vnni:
                logger.info("  AVX-VNNI: aktiviert (AI-Beschleunigung)")

        except Exception as e:
            logger.warning(f"CPU Detection Fehler: {e}")
            self.config.available_accelerators.append(AcceleratorType.CPU_BASIC)

    def _parse_lscpu(self) -> None:
        try:
            result = subprocess.run(["lscpu"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return
            for line in result.stdout.split("\n"):
                if "l3 cache" in line.lower():
                    match = re.search(r"(\d+)", line.split(":")[1])
                    if match:
                        val = int(match.group(1))
                        self.config.cpu.l3_cache_mb = val if val < 1000 else val // 1024
                if "cpu max mhz" in line.lower():
                    match = re.search(r"([\d.]+)", line.split(":")[1])
                    if match:
                        self.config.cpu.max_mhz = float(match.group(1))
        except Exception:
            pass

    def _detect_hybrid_topology(self) -> None:
        if self.config.cpu.architecture not in [
            CPUArchitecture.INTEL_ARROW_LAKE,
            CPUArchitecture.INTEL_METEOR_LAKE,
            CPUArchitecture.INTEL_RAPTOR_LAKE,
            CPUArchitecture.INTEL_ALDER_LAKE,
        ]:
            return

        model = self.config.cpu.model.lower()
        total = self.config.cpu.cores

        # Bekannte Konfigurationen
        if "ultra 7 265" in model:
            self.config.cpu.p_cores = 8
            self.config.cpu.e_cores = 4
            self.config.cpu.lpe_cores = 8
        elif "ultra 9 285" in model:
            self.config.cpu.p_cores = 8
            self.config.cpu.e_cores = 16
        elif "ultra 5 245" in model:
            self.config.cpu.p_cores = 6
            self.config.cpu.e_cores = 8
        else:
            self.config.cpu.p_cores = max(4, total * 6 // 10)
            self.config.cpu.e_cores = total - self.config.cpu.p_cores

        if self.config.cpu.p_cores > 0:
            logger.info(f"  Hybrid: {self.config.cpu.p_cores}P + {self.config.cpu.e_cores}E + {self.config.cpu.lpe_cores}LP-E")

    def _detect_cuda(self) -> bool:
        try:
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
                logger.info(f"CUDA: {len(self.config.gpus)} GPU(s)")
                return True
        except FileNotFoundError:
            pass
        return False

    def _detect_rocm(self) -> bool:
        try:
            result = subprocess.run(["rocminfo"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return False

            gpu_count = 0
            for line in result.stdout.split("\n"):
                if "Name:" in line and "gfx" in line.lower():
                    gpu_count += 1

            if gpu_count > 0:
                self.config.available_accelerators.append(AcceleratorType.ROCM)
                logger.info(f"ROCm: {gpu_count} GPU(s)")
                return True
        except FileNotFoundError:
            pass
        return False

    def _detect_oneapi(self) -> bool:
        if Path("/opt/intel/oneapi").exists():
            self.config.available_accelerators.append(AcceleratorType.ONEAPI)
            logger.info("Intel oneAPI: erkannt")
            return True
        return False

    def _detect_system_memory(self) -> None:
        try:
            if Path("/proc/meminfo").exists():
                meminfo = Path("/proc/meminfo").read_text()
                for line in meminfo.split("\n"):
                    if "MemTotal:" in line:
                        kb = int(line.split()[1])
                        self.config.total_system_memory = kb // 1024
                        break
            logger.info(f"System RAM: {self.config.total_system_memory} MB")
        except Exception as e:
            logger.warning(f"Memory Detection: {e}")

    def _determine_primary_accelerator(self) -> None:
        priority = [
            AcceleratorType.CUDA,
            AcceleratorType.ROCM,
            AcceleratorType.ONEAPI,
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
        cpu = self.config.cpu

        if self.config.total_gpu_memory > 0:
            self.config.recommended_batch_size = min(64, max(1, self.config.total_gpu_memory // 1024 * 8))
        else:
            self.config.recommended_batch_size = min(8, cpu.cores)

        # Thread-Empfehlungen für Hybrid CPUs
        if cpu.is_hybrid:
            self.config.recommended_p_core_threads = cpu.p_cores
            self.config.recommended_e_core_threads = cpu.e_cores
            # Für I/O-bound FastAPI: Alle Cores nutzen
            self.config.recommended_threads = cpu.cores
            # Workers: 2 * P-Cores + 1 (P-Cores sind wichtiger für Request-Handling)
            self.config.recommended_workers = min(cpu.p_cores * 2 + 1, cpu.cores)
        else:
            self.config.recommended_threads = max(4, cpu.cores - 2)
            self.config.recommended_workers = max(4, cpu.cores - 2)

        logger.info(f"  Empfohlene Workers: {self.config.recommended_workers}")
        logger.info(f"  Empfohlene Threads: {self.config.recommended_threads}")

    def _setup_environment(self) -> None:
        env = self.config.env_vars
        cpu = self.config.cpu

        # Thread-Konfiguration
        env["OMP_NUM_THREADS"] = str(self.config.recommended_threads)
        env["MKL_NUM_THREADS"] = str(self.config.recommended_threads)
        env["OPENBLAS_NUM_THREADS"] = str(self.config.recommended_threads)
        env["NUMEXPR_NUM_THREADS"] = str(self.config.recommended_threads)

        # DNNL ISA - WICHTIG: Arrow Lake hat kein AVX-512!
        if cpu.avx512 and not cpu.is_arrow_lake:
            env["DNNL_MAX_CPU_ISA"] = "AVX512_CORE_AMX"
        elif cpu.avx2:
            env["DNNL_MAX_CPU_ISA"] = "AVX2"

        # Intel Hybrid CPU Optimierungen
        if cpu.is_hybrid:
            env["MALLOC_ARENA_MAX"] = "4"
            env["KMP_AFFINITY"] = "granularity=fine,compact"
            env["KMP_BLOCKTIME"] = "0"
            
            if cpu.is_arrow_lake:
                # Arrow Lake spezifisch
                env["GOMP_CPU_AFFINITY"] = f"0-{cpu.cores - 1}"
                env["MALLOC_TRIM_THRESHOLD_"] = "131072"
                env["MALLOC_MMAP_MAX_"] = "65536"
                logger.info("Arrow Lake Optimierungen aktiviert")

        # GPU Settings
        if AcceleratorType.CUDA in self.config.available_accelerators:
            env["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
            env["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"

        if AcceleratorType.ROCM in self.config.available_accelerators:
            env["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"
            env["ROCM_PATH"] = "/opt/rocm"

        env["TOKENIZERS_PARALLELISM"] = "true"

        for key, value in env.items():
            os.environ[key] = value

    def _log_config(self) -> None:
        logger.info("=== Hardware-Konfiguration ===")
        logger.info(f"  Primary: {self.config.primary_accelerator.name}")
        logger.info(f"  GPUs: {len(self.config.gpus)}")
        logger.info(f"  GPU VRAM: {self.config.total_gpu_memory} MB")
        logger.info(f"  System RAM: {self.config.total_system_memory} MB")
        logger.info(f"  Workers: {self.config.recommended_workers}")
        logger.info(f"  Threads: {self.config.recommended_threads}")
        logger.info("==============================")

    def get_pytorch_device(self) -> str:
        if AcceleratorType.CUDA in self.config.available_accelerators:
            return "cuda"
        elif AcceleratorType.ROCM in self.config.available_accelerators:
            return "cuda"
        elif AcceleratorType.METAL in self.config.available_accelerators:
            return "mps"
        return "cpu"

    def get_onnx_providers(self) -> List[str]:
        providers = []
        if AcceleratorType.CUDA in self.config.available_accelerators:
            providers.extend(["CUDAExecutionProvider", "TensorrtExecutionProvider"])
        if AcceleratorType.ROCM in self.config.available_accelerators:
            providers.append("ROCMExecutionProvider")
        if AcceleratorType.ONEAPI in self.config.available_accelerators:
            providers.append("OpenVINOExecutionProvider")
        providers.append("CPUExecutionProvider")
        return providers

    def get_llama_cpp_args(self) -> Dict[str, Any]:
        args = {
            "n_threads": self.config.recommended_threads,
            "n_batch": self.config.recommended_batch_size * 512,
        }
        if AcceleratorType.CUDA in self.config.available_accelerators:
            args["n_gpu_layers"] = -1
        elif AcceleratorType.ROCM in self.config.available_accelerators:
            args["n_gpu_layers"] = -1
        return args

    def get_uvicorn_config(self) -> Dict[str, Any]:
        """Gibt optimale Uvicorn-Konfiguration zurück"""
        return {
            "workers": self.config.recommended_workers,
            "loop": "uvloop",
            "http": "httptools",
            "limit_concurrency": self.config.recommended_workers * 10,
            "timeout_keep_alive": 30,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_accelerator": self.config.primary_accelerator.name,
            "available_accelerators": [a.name for a in self.config.available_accelerators],
            "gpus": [{"index": g.index, "name": g.name, "memory_mb": g.memory_total} for g in self.config.gpus],
            "cpu": {
                "model": self.config.cpu.model,
                "architecture": self.config.cpu.architecture.value,
                "cores": self.config.cpu.cores,
                "p_cores": self.config.cpu.p_cores,
                "e_cores": self.config.cpu.e_cores,
                "lpe_cores": self.config.cpu.lpe_cores,
                "avx2": self.config.cpu.avx2,
                "avx512": self.config.cpu.avx512,
                "avx_vnni": self.config.cpu.avx_vnni,
                "l3_cache_mb": self.config.cpu.l3_cache_mb,
                "max_mhz": self.config.cpu.max_mhz,
            },
            "total_gpu_memory_mb": self.config.total_gpu_memory,
            "total_system_memory_mb": self.config.total_system_memory,
            "recommended_batch_size": self.config.recommended_batch_size,
            "recommended_threads": self.config.recommended_threads,
            "recommended_workers": self.config.recommended_workers,
            "uvicorn_config": self.get_uvicorn_config(),
            "pytorch_device": self.get_pytorch_device(),
            "onnx_providers": self.get_onnx_providers(),
        }


# === Singleton ===
_detector: Optional[HardwareDetector] = None


def get_hardware_config() -> HardwareConfig:
    global _detector
    if _detector is None:
        _detector = HardwareDetector()
        _detector.detect_all()
    return _detector.config


def get_hardware_detector() -> HardwareDetector:
    global _detector
    if _detector is None:
        _detector = HardwareDetector()
        _detector.detect_all()
    return _detector


def get_device() -> str:
    return get_hardware_detector().get_pytorch_device()


def get_threads() -> int:
    return get_hardware_config().recommended_threads


def get_workers() -> int:
    return get_hardware_config().recommended_workers


def get_batch_size() -> int:
    return get_hardware_config().recommended_batch_size


def init_hardware_acceleration() -> Dict[str, Any]:
    detector = get_hardware_detector()
    config = detector.to_dict()
    logger.info("Hardware Acceleration v2.0 initialisiert")
    return config
