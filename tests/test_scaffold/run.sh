#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NPKC="${NPKC:-/home/randy/Workspace/REPOS/nitpick/build/npkc}"

echo "=== test_scaffold ==="
"$NPKC" "$SCRIPT_DIR/main.npk" -o "$SCRIPT_DIR/test_bin" 2>&1 | grep -v "^\[DEBUG"
"$SCRIPT_DIR/test_bin"
rm -f "$SCRIPT_DIR/test_bin"
