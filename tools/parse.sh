#!/bin/bash

# --- 1. Auto-Discovery Logic ---
ARGS=""

# Logic for ROOT-based flags
[[ -z "$GCC_ROOT" ]]     && ARGS+="-DUSE_SYSTEM_GCC=1 "
[[ -z "$CUDA_ROOT" ]]    && ARGS+="-Dwithout_cuda=1 "
[[ -z "$ROCM_ROOT" ]]    && ARGS+="-Dwithout_rocm=1 "
[[ -n "$VECGEOM_ROOT" ]] && ARGS+="-Denable_vecgeom=1 "

# --- NEW: Microarchitecture Comparison Logic ---
# Handle the comparison here in the shell where strings work.
if [[ -n "$default_microarch_name" && -n "$min_microarch_name" ]]; then
    if [[ "$default_microarch_name" != "$min_microarch_name" ]]; then
        ARGS+="-DARCH_DIFF=1 "
    else
        ARGS+="-DARCH_DIFF=0 "
    fi
fi

# --- 2. Microarchitecture Logic (Values) ---
for arch_var in "default_microarch_name" "min_microarch_name"; do
    if [[ -v $arch_var ]]; then
        val=$(echo "${!arch_var}" | grep -o '[0-9]\+')
        if [ -n "$val" ]; then
            ARGS+="-D$arch_var=$val "
        fi
    fi
done

# --- 3. Pass-through for other variables ---
[[ -n "$HFI_NO_BACKTRACE" ]]   && ARGS+="-DHFI_NO_BACKTRACE=$HFI_NO_BACKTRACE "
[[ -n "$IPATH_NO_BACKTRACE" ]] && ARGS+="-DIPATH_NO_BACKTRACE=$IPATH_NO_BACKTRACE "
[[ -n "$enable_frame_pointer" ]] && ARGS+="-Denable_frame_pointer=$enable_frame_pointer "

echo "Executing with flags: $ARGS"

# --- 4. Recursive Processing ---
xml_files=$(find . -name "*.xml")

for file in $xml_files; do
    [ "$file" == "./$0" ] && continue
    echo "Rewriting $file..."
    
    # We pipe through a quick sed to normalize the logic line to use our new flag
    # This turns 'default_microarch_name != min_microarch_name' into 'ARCH_DIFF'
    cat "$file" | sed 's/default_microarch_name != min_microarch_name/ARCH_DIFF/g' > "$file.prepped"

    if gcc -E -P -x c $ARGS "$file.prepped" -o "$file.tmp"; then
        mv "$file.tmp" "$file"
        rm -f "$file.prepped"
    else
        echo "Error: Failed to process $file."
        rm -f "$file.tmp" "$file.prepped"
    fi
done

echo "All XML files have been updated in place."
