#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== NPKDB v0.5.3 Z3 Verification Test ==="
cd "${REPO_ROOT}"

mkdir -p build

NPKC="/home/randy/Workspace/REPOS/nitpick/build/npkc"

echo "Compiling prefix_extractor with Z3 verification using: $NPKC"
$NPKC tests/test_prefix_extractor/main.npk --verify-contracts -o build/test_prefix_extractor_bin

echo "=== Z3 Verification Passed! ==="
