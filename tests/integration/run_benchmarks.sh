#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "Cleaning up old data..."
rm -rf data/ wal.log server*.log

echo "Starting NPKDB Server on a single core (CPU 0)..."
taskset -c 0 ./build/npkdb_server > server_bench.log 2>&1 &
SERVER_PID=$!

sleep 2

echo "Running write benchmark..."
python3 scripts/bench_write.py

echo "Running read benchmark..."
python3 scripts/bench_read.py

echo "Shutting down server..."
kill $SERVER_PID || true
wait $SERVER_PID || true

echo "Benchmarks complete."
