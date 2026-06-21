#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== NPKDB v0.3.11 E2E Integration Test ==="
cd "${REPO_ROOT}"

mkdir -p build
echo "[1] Compiling npkdb_server..."
/home/randy/Workspace/REPOS/nitpick/build/npkc src/main.npk -o build/npkdb_server

echo "[2] Starting background server..."
./build/npkdb_server &
SERVER_PID=$!

# Ensure we kill the server on exit
trap 'echo "Killing server (PID $SERVER_PID)..."; kill -9 $SERVER_PID 2>/dev/null || true' EXIT

# Wait for bind
sleep 1

# Check if server is running
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "ERROR: Server failed to start or crashed."
    exit 1
fi

echo "[3] Executing curl test sequence..."

# Create collection
echo " -> Creating collection 'test_collection'..."
curl -s -X POST http://127.0.0.1:8080/collections \
    -H "Content-Type: application/json" \
    -d '{"name": "test_collection"}' | jq -e '.status == "ok"' > /dev/null

# Insert 3 documents
echo " -> Inserting documents..."
curl -s -X PUT http://127.0.0.1:8080/collections/test_collection/docs \
    -H "Content-Type: application/json" \
    -d '[
          {"_id": "doc1", "vector": [1.0, 2.0], "meta": "a"},
          {"_id": "doc2", "vector": [1.1, 2.1], "meta": "b"},
          {"_id": "doc3", "vector": [1.2, 2.2], "meta": "c"}
        ]' | jq -e '.status == "ok"' > /dev/null

# Search with filter
echo " -> Searching for nearest neighbor with meta == 'b'..."
SEARCH_RES=$(curl -s -X POST http://127.0.0.1:8080/search \
    -H "Content-Type: application/json" \
    -d '{"collection": "test_collection", "vector": [1.0, 2.0], "k": 1, "filter": {"meta": {"$eq": "b"}}}')

echo "Search Response: $SEARCH_RES"

# Assert we got doc2
echo "$SEARCH_RES" | jq -e '.results[0].document_id == "doc2"' > /dev/null

echo "=== E2E Integration Test Passed! ==="
