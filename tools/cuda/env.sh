SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../bin/os_libdir.sh"

# cuda-flags.file uses cmsdist's CMS_CXX_STD name, while BITS provides CXXSTD.
# This script runs before fix_tool_variables expands the CUDA XML placeholders.
cuda_cxx_std="${CXXSTD:-${CMS_CXX_STANDARD:-20}}"
export CMS_CXX_STD="$cuda_cxx_std"
export CUDA_HOST_CXXFLAGS="-std=c++${cuda_cxx_std}"
export CUDA_FLAGS="${CUDA_FLAGS/-std=c++ /-std=c++${cuda_cxx_std} }"
