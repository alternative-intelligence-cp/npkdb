#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NPKC="${NPKC:-/home/randy/Workspace/REPOS/nitpick/build/npkc}"

echo "=== test_verify_contracts ==="

# We compile this specific harness with contract verification
"$NPKC" "$SCRIPT_DIR/main.npk" --verify-contracts

echo "test_verify_contracts complete!"
