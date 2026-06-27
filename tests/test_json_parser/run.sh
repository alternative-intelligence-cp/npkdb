#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== NPKDB v0.3.1 — JSON Parser ==="
cd "${REPO_ROOT}"
mkdir -p test_json_parser
/home/randy/Workspace/REPOS/nitpick/build/npkc tests/test_json_parser/main.npk -o tests/test_json_parser/main_bin
./tests/test_json_parser/main_bin
echo "=== Done ==="
