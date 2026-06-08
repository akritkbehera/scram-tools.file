if [ -n "$CUDA_REVISION" ]; then
  export USE_CUDA=0
fi

if [ -n "$ROCM_REVISION" ]; then
  export USE_ROCM=0
fi
