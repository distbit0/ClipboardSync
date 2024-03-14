#!/bin/bash
source /home/pimania/dev/guiFromCron/crongui.sh
script_dir="$(dirname "$0")"
python3 "$script_dir/receive.py"