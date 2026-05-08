include(`macros.m4')dnl
<tool revision="5">
  <lib name="mpi"/>
  <client>
    <environment name="LIBDIR"       default="$TOOL_BASE/lib"/>
    <environment name="INCLUDE"      default="$TOOL_BASE/include"/>
  </client>
  <runtime name="PATH" value="$TOOL_BASE/bin" type="path"/>
  <runtime name="OPAL_PREFIX" value="$TOOL_BASE"/>
  <runtime name="PMIX_PREFIX" value="$TOOL_BASE"/>
  <runtime name="OMPI_MCA_accelerator" value="null"/>
  IFENV(`',`<runtime name="HFI_NO_BACKTRACE" value="GETENV(`HFI_NO_BACKTRACE')"/>',`HFI_NO_BACKTRACE')
  IFENV(`',`<runtime name="IPATH_NO_BACKTRACE" value="GETENV(`IPATH_NO_BACKTRACE')"/>',`IPATH_NO_BACKTRACE')
</tool>
