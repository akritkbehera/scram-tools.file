include(`macros.m4')dnl
<tool type="compiler" revision="2">
  <use name="gcc-f77compiler"/>
  <client>
   IFENV(`<environment name="FC" default="gfortran"/>',`<environment name="FC" default="@GCC_ROOT@/bin/gfortran"/>',`GCC_ROOT')
  </client>
</tool>
