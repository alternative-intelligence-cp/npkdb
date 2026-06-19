#!/bin/bash
set -e

# Use NPKC from env, fallback to nitpick
NPKC="${NPKC:-/home/randy/Workspace/REPOS/nitpick/build/npkc}"

cd "$(dirname "$0")/../.."

echo "=== test_compaction ==="
rm -rf test_comp_data
$NPKC tests/test_compaction/main.npk -o tests/test_compaction/test_compaction
./tests/test_compaction/test_compaction
