#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "Running Integration Tests..."

# We assume npkc is built at ../../../nitpick/build/npkc
NPKC="../../../nitpick/build/npkc"

if [ ! -f "$NPKC" ]; then
    echo "Compiler not found at $NPKC"
    exit 1
fi

FAILED=0

run_test() {
    local test_file=$1
    local bin_name="${test_file%.npk}_bin"
    
    echo "Compiling $test_file..."
    if ! $NPKC "$test_file" -o "$bin_name"; then
        echo "Failed to compile $test_file"
        FAILED=$((FAILED + 1))
        return
    fi
    
    echo "Running $bin_name..."
    if ! ./"$bin_name"; then
        echo "Test $test_file FAILED"
        FAILED=$((FAILED + 1))
    else
        echo "Test $test_file PASSED"
    fi
    echo "----------------------------------------"
}

run_test test_roundtrip.npk
run_test test_crash_recovery.npk
run_test test_compaction_correctness.npk
run_test test_stress.npk

if [ $FAILED -gt 0 ]; then
    echo "Integration tests: $FAILED failed."
    exit 1
fi

echo "All Integration tests passed!"
exit 0
