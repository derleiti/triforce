#!/bin/bash
set -euo pipefail
RUN_DIR="/run/triforce"
OUT_FILE="$RUN_DIR/hw.env"
mkdir -p "$RUN_DIR"
trim() { sed 's/^[[:space:]]*//;s/[[:space:]]*$//'; }

cpu_vendor="unknown"
cpu_model="unknown"
cpu_arch="$(uname -m)"
cpu_threads="$(nproc 2>/dev/null || echo 1)"
cpu_cores_physical="$cpu_threads"
cpu_flags="$(grep -m1 '^flags' /proc/cpuinfo 2>/dev/null || true)"
gpu_backend="none"
gpu_vendor="none"
gpu_model="none"
gpu_count=0
runtime_mode="cpu-generic"
hw_class="general-node"
cpu_isa="none"

if echo "$cpu_flags" | grep -qw avx512f; then
  cpu_isa="avx512"
elif echo "$cpu_flags" | grep -qw avx2; then
  cpu_isa="avx2"
fi

if command -v lscpu >/dev/null 2>&1; then
  cpu_model="$(lscpu | awk -F: '/Model name:/ {print $2; exit}' | trim)"
  vendor_raw="$(lscpu | awk -F: '/Vendor ID:/ {print $2; exit}' | trim)"
  cores_per_socket="$(lscpu | awk -F: '/Core\(s\) per socket:/ {print $2; exit}' | trim)"
  sockets="$(lscpu | awk -F: '/Socket\(s\):/ {print $2; exit}' | trim)"
  if [[ -n "${cores_per_socket:-}" && -n "${sockets:-}" && "$cores_per_socket" =~ ^[0-9]+$ && "$sockets" =~ ^[0-9]+$ ]]; then
    cpu_cores_physical=$((cores_per_socket * sockets))
  fi
  case "$vendor_raw" in
    GenuineIntel) cpu_vendor="intel" ;;
    AuthenticAMD) cpu_vendor="amd" ;;
  esac
fi

if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  gpu_backend="cuda"
  gpu_vendor="nvidia"
  gpu_model="$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n1 | trim)"
  gpu_count="$(nvidia-smi -L | wc -l | tr -d ' ')"
elif command -v rocminfo >/dev/null 2>&1 && rocminfo >/dev/null 2>&1; then
  gpu_backend="rocm"
  gpu_vendor="amd"
  gpu_model="$(rocminfo 2>/dev/null | awk -F': ' '/Marketing Name|Name:/ {print $2; exit}' | trim)"
  [[ -z "$gpu_model" ]] && gpu_model="amd-gpu"
  gpu_count=1
elif command -v rocm-smi >/dev/null 2>&1 && rocm-smi >/dev/null 2>&1; then
  gpu_backend="rocm"
  gpu_vendor="amd"
  gpu_model="$(rocm-smi --showproductname 2>/dev/null | awk -F': ' '/Card series|Card model/ {print $2; exit}' | trim)"
  [[ -z "$gpu_model" ]] && gpu_model="amd-gpu"
  gpu_count=1
elif command -v clinfo >/dev/null 2>&1 && clinfo >/dev/null 2>&1; then
  gpu_backend="opencl"
  gpu_vendor="unknown"
  gpu_model="$(clinfo 2>/dev/null | awk -F': ' '/Device Name/ {print $2; exit}' | trim)"
  [[ -z "$gpu_model" ]] && gpu_model="opencl-device"
  gpu_count=1
fi

runtime_mode="cpu-$cpu_vendor"
if [[ "$gpu_backend" == "cuda" ]]; then
  runtime_mode="hybrid-cuda"
elif [[ "$gpu_backend" == "rocm" ]]; then
  runtime_mode="hybrid-rocm"
elif [[ "$gpu_backend" == "opencl" ]]; then
  runtime_mode="gpu-opencl"
fi

if (( cpu_cores_physical <= 4 )); then
  uvicorn_workers=2
  hw_class="minimal-node"
elif (( cpu_cores_physical <= 8 )); then
  uvicorn_workers=4
  hw_class="general-node"
elif (( cpu_cores_physical <= 16 )); then
  uvicorn_workers=8
  hw_class="performance-node"
else
  uvicorn_workers=$((cpu_cores_physical / 2))
  (( uvicorn_workers > 12 )) && uvicorn_workers=12
  hw_class="server-heavy"
fi

if [[ "$gpu_backend" != "none" ]]; then
  hw_class="gpu-node"
fi

thread_pool=$((cpu_threads - 2))
(( thread_pool < 2 )) && thread_pool=2
max_concurrent=$((uvicorn_workers * 10))

cat > "$OUT_FILE" <<EOENV
TRIFORCE_CPU_VENDOR="$cpu_vendor"
TRIFORCE_CPU_MODEL="$cpu_model"
TRIFORCE_CPU_ARCH="$cpu_arch"
TRIFORCE_CPU_CORES_PHYSICAL="$cpu_cores_physical"
TRIFORCE_CPU_THREADS="$cpu_threads"
TRIFORCE_CPU_ISA="$cpu_isa"
TRIFORCE_GPU_BACKEND="$gpu_backend"
TRIFORCE_GPU_VENDOR="$gpu_vendor"
TRIFORCE_GPU_MODEL="$gpu_model"
TRIFORCE_GPU_COUNT="$gpu_count"
TRIFORCE_RUNTIME_MODE="$runtime_mode"
TRIFORCE_HW_CLASS="$hw_class"
TRIFORCE_UVICORN_WORKERS="$uvicorn_workers"
TRIFORCE_THREAD_POOL="$thread_pool"
TRIFORCE_MAX_CONCURRENT="$max_concurrent"
EOENV
chmod 0644 "$OUT_FILE"
echo "[detect-hardware] wrote $OUT_FILE"
cat "$OUT_FILE"
