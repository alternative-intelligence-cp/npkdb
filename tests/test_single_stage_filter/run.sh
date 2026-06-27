#!/bin/bash
set -e

echo "Building test_single_stage_filter..."
/home/randy/Workspace/REPOS/nitpick/build/npkc test_single_stage_filter/main.npk -o test_single_stage_filter/main_bin

echo "Running test_single_stage_filter..."
./test_single_stage_filter/main_bin
