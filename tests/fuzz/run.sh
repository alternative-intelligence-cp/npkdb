#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== NPKDB v0.4.0 Fuzz Testing ==="
cd "${REPO_ROOT}"

mkdir -p build

NPKC="/home/randy/Workspace/REPOS/nitpick/build/npkc"

echo "Compiling harness_json..."
$NPKC fuzz/harness_json.npk -o build/fuzz_json_bin

echo "Running fuzzer..."
python3 scripts/fuzz_json.py

echo "=== Fuzz Test Passed! Zero segfaults. ==="
