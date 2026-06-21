#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== NPKDB v0.3.12 Z3 Verification Test ==="
cd "${REPO_ROOT}"

mkdir -p build

NPKC="/home/randy/Workspace/REPOS/nitpick/build/npkc"

echo "Compiling with Z3 verification using: $NPKC"
$NPKC src/main.npk --verify-contracts -o build/npkdb_server_verified

echo "=== Z3 Verification Passed! ==="
