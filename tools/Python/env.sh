export PYTHON3V=$("$TOOL_ROOT/bin/python3" -V 2>&1 | awk '{print $2}' | cut -f1,2 -d.)
export PYTHONV="$PYTHON3V"
