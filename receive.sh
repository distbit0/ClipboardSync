#!/bin/bash

# Get the directory of the currently executing script
script_dir="$(dirname "$0")"

# Execute the Python script
python3 "$script_dir/receive.py"
