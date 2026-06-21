#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
NPK="${NPK_BIN:-npk}"

echo "=== NPKDB v0.3.0 — JSON Model ==="
cd "${REPO_ROOT}"
/home/randy/Workspace/REPOS/nitpick/build/npkc tests/test_json_model/main.npk -o tests/test_json_model/main_bin
./tests/test_json_model/main_bin
echo "=== Done ==="
