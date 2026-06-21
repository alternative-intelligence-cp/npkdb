#!/bin/bash
set -e

# Change into project root
cd "$(dirname "$0")/../.."

echo "Building test_collections..."
/home/randy/Workspace/REPOS/nitpick/build/npkc tests/test_collections/main.npk -o tests/test_collections/main_bin

echo "Running test_collections..."
./tests/test_collections/main_bin
