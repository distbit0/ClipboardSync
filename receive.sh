#!/bin/bash
export DISPLAY=:0.0 >/dev/null 2>&1
# Get the directory of the currently executing script
script_dir="$(dirname "$0")"

# Execute the Python script
python3 "$script_dir/receive.py"
