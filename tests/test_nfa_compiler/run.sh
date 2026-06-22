#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== NPKDB v0.5.2 Z3 Verification Test ==="
cd "${REPO_ROOT}"

mkdir -p build

NPKC="/home/randy/Workspace/REPOS/nitpick/build/npkc"

echo "Compiling nfa_compiler with Z3 verification using: $NPKC"
$NPKC tests/test_nfa_compiler/main.npk --verify-contracts -o build/test_nfa_compiler_bin

echo "=== Z3 Verification Passed! ==="
