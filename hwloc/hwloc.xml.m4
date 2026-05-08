include(`macros.m4')dnl
<tool revision="3">
  <lib name="hwloc"/>
  <client>
    <environment name="INCLUDE"     default="$TOOL_BASE/include/hwloc"/>
    <environment name="LIBDIR"      default="$TOOL_BASE/lib"/>
  </client>
  <runtime name="PATH" value="$TOOL_BASE/bin" type="path"/>
  IFENV(`',`<runtime name="HWLOC_PLUGINS_PATH" value="$TOOL_BASE/lib/hwloc" type="path"/>',`ROCM_ROOT')
  IFENV(`',`<runtime name="HWLOC_PLUGINS_PATH" value="$TOOL_BASE/lib/hwloc" type="path"/>',`CUDA_ROOT')
</tool>
