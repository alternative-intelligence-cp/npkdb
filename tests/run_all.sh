#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
echo "=== NPKDB Full Test Suite ==="
FAILED=0

for test_dir in test_*/; do
    if [ -f "${test_dir}run.sh" ]; then
        echo ""
        echo "--- Running $test_dir ---"
        if ! ./"${test_dir}run.sh"; then
            FAILED=$((FAILED + 1))
        fi
    fi
done

echo ""
if [ $FAILED -gt 0 ]; then
    echo "FAILED: $FAILED test suite(s) had failures"
    exit 1
fi
echo "ALL TEST SUITES PASSED"
exit 0
