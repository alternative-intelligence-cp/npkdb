#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NPKC="${NPKC:-/home/randy/Workspace/REPOS/nitpick/build/npkc}"
BUILD_DIR="$(dirname "$SCRIPT_DIR")/../build"
mkdir -p "$BUILD_DIR"

echo "=== test_bloom ==="
"$NPKC" "$SCRIPT_DIR/main.npk" -o "$BUILD_DIR/test_bloom_bin" 2>&1 | grep -v "^\[DEBUG"
"$BUILD_DIR/test_bloom_bin"
rm -f "$BUILD_DIR/test_bloom_bin"
