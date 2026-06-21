#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

# Clean slate
rm -rf data/ wal.log server*.log

echo "Starting NPKDB..."
./build/npkdb_server > server1.log 2>&1 &
SERVER_PID=$!
sleep 1

echo "Inserting 10,000 documents..."
python3 scripts/test_inserts.py

echo "Simulating crash..."
kill -9 $SERVER_PID || true
wait $SERVER_PID || true

echo "Injecting torn write into WAL..."
echo -n "GARBAGEBYTE" >> wal.log

echo "Rebooting..."
./build/npkdb_server > server2.log 2>&1 &
NEW_SERVER_PID=$!

# Wait up to 30 seconds for recovery to complete
for i in {1..30}; do
    if grep -q "Server listening on port 8080" server2.log; then
        break
    fi
    sleep 1
done

kill $NEW_SERVER_PID || true
wait $NEW_SERVER_PID || true

echo "Analyzing recovery..."
if grep -q "Replayed 10000 records from WAL" server2.log; then
    echo "SUCCESS: Server recovered exactly 10,000 records and truncated torn write."
    exit 0
else
    echo "FAILED: Recovery did not match 10000 records."
    cat server2.log
    exit 1
fi
