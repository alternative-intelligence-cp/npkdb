#!/bin/bash
set -e

# Change into project root
cd "$(dirname "$0")/../.."

echo "Building test_http_core..."
/home/randy/Workspace/REPOS/nitpick/build/npkc tests/test_http_core/main.npk -o tests/test_http_core/main_bin

echo "Starting Server in background..."
./tests/test_http_core/main_bin &
SERVER_PID=$!

echo "Waiting for server to bind (500ms)..."
sleep 0.5

echo "Testing / with curl..."
RESPONSE=$(curl -s http://127.0.0.1:8081/ || true)
echo "Response: $RESPONSE"

if [[ "$RESPONSE" == *"npkdb"* ]]; then
    echo "✓ Curl test passed!"
    kill $SERVER_PID
    exit 0
else
    echo "✗ Curl test failed!"
    kill $SERVER_PID
    exit 1
fi

echo "Waiting for test thread to auto-exit the server..."
wait $SERVER_PID
echo "Server exited successfully."
