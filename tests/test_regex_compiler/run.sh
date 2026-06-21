#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== NPKDB v0.5.1 Z3 Verification Test ==="
cd "${REPO_ROOT}"

mkdir -p build

NPKC="/home/randy/Workspace/REPOS/nitpick/build/npkc"

echo "Compiling regex_compiler with Z3 verification using: $NPKC"
$NPKC tests/test_regex_compiler/main.npk --verify-contracts -o build/test_regex_compiler_bin

echo "=== Z3 Verification Passed! ==="
