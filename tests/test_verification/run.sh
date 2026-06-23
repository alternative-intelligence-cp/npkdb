#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NPKC="${NPKC:-/home/randy/Workspace/REPOS/nitpick/build/npkc}"
SRC_DIR="$(dirname "$SCRIPT_DIR")/../src"
TESTS_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== test_verification ==="

# 1. Z3 Constraint Checking
echo "[1/4] Running Z3 constraint checks on NPKDB Core..."
"$NPKC" "$SRC_DIR/main.npk" --verify 2>&1 | grep -v "^\[DEBUG" || true

# 2. Z3 Concurrency Checking
echo "[2/4] Running Z3 concurrency checks on NPKDB Core..."
"$NPKC" "$SRC_DIR/main.npk" --verify-concurrency 2>&1 | grep -v "^\[DEBUG" || true
echo "[2/4] Running Z3 concurrency checks on SkipList..."
"$NPKC" "$TESTS_DIR/test_skiplist/main.npk" --verify-concurrency 2>&1 | grep -v "^\[DEBUG" || true

# 3. Z3 Math, Memory & Contracts Checks
echo "[3/4] Running Z3 mathematical overflow checks..."
"$NPKC" "$SRC_DIR/main.npk" --verify-overflow 2>&1 | grep -v "^\[DEBUG" || true
echo "[3/4] Running Z3 memory safety checks..."
"$NPKC" "$SRC_DIR/main.npk" --verify-memory 2>&1 | grep -v "^\[DEBUG" || true
echo "[3/4] Running Z3 strict contract verification..."
"$NPKC" "$SRC_DIR/main.npk" --verify-contracts 2>&1 | grep -v "^\[DEBUG" || true

# 4. NIKOS Abstract Interpretation
echo "[4/4] Running NIKOS memory safety analysis on NPKDB Core..."
"$NPKC" "$SRC_DIR/main.npk" --verify-nikos 2>&1 | grep -v "^\[DEBUG" || true

echo "Verification pass complete!"
