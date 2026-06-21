#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if ! command -v wrk &> /dev/null; then
    echo "wrk could not be found. Please install."
    exit 1
fi

if [ ! -f "scripts/bulk_insert.json" ]; then
    echo "Generating bulk insert payload..."
    python3 scripts/generate_payload.py
fi

echo "Cleaning up old data..."
rm -rf data/ wal.log server*.log

echo "Starting NPKDB Server..."
./build/npkdb_server > server_stress.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
sleep 2

echo "Starting concurrent write stress test (12 threads, 200 connections, 5 seconds)..."
# We'll use 5 seconds to avoid OOM due to Nitpick string leaks
wrk -t12 -c200 -d5s -s scripts/wrk_insert.lua http://127.0.0.1:8080/collections/default/docs

echo "Wrk finished. Waiting 10 seconds for background compactions to settle..."
sleep 10

echo "Shutting down server safely..."
kill $SERVER_PID || true
wait $SERVER_PID || true

echo "Done."
