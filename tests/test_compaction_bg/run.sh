#!/bin/bash
set -e

# Use NPKC from env, fallback to nitpick
NPKC="${NPKC:-/home/randy/Workspace/REPOS/nitpick/build/npkc}"

cd "$(dirname "$0")/../.."

echo "=== test_compaction_bg ==="
rm -rf test_bg_data
mkdir -p test_bg_data
$NPKC tests/test_compaction_bg/main.npk -o tests/test_compaction_bg/test_compaction_bg
./tests/test_compaction_bg/test_compaction_bg
