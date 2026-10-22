if [ -n "${CUDA_ROOT:-}" ] || [ -n "${ROCM_ROOT:-}" ]; then
  export HWLOC_GPU_ENABLED=1
else
  export HWLOC_GPU_ENABLED=0
fi
