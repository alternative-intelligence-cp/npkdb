#!/bin/bash
./build/npkdb_server > server_crash.log 2>&1 &
SERVER_PID=$!
sleep 1
curl -X POST -d '{"data": "hello"}' http://localhost:8080/put/test_key || true
sleep 1
kill $SERVER_PID || true
