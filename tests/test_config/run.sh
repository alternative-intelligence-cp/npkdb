#!/bin/bash
set -e

# Change into project root
cd "$(dirname "$0")/../.."

echo "Building test_config..."
/home/randy/Workspace/REPOS/nitpick/build/npkc tests/test_config/main.npk -o tests/test_config/main_bin

echo "Running test_config..."
./tests/test_config/main_bin
