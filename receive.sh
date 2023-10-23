#!/bin/bash
export XAUTHORITY=`ls  /run/user/1000/.* | grep mutt`;
export DISPLAY=:0
# Get the directory of the currently executing script
script_dir="$(dirname "$0")"

# Execute the Python script
python3 "$script_dir/receive.py"
