#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== NPKDB v0.3.10 — HTTP Errors ==="
cd "${REPO_ROOT}"
mkdir -p tests/test_http_errors

cp src/network/controllers.npk tests/test_http_errors/controllers_mock.npk
cp src/network/router.npk tests/test_http_errors/router_mock.npk
cp src/network/errors.npk tests/test_http_errors/errors_mock.npk

# Patch the Server.send_typed references
sed -i 's/raw Server.send_typed/send_typed/g' tests/test_http_errors/controllers_mock.npk
sed -i 's/Server.send_typed/send_typed/g' tests/test_http_errors/controllers_mock.npk
sed -i 's/raw Server.send_typed/send_typed/g' tests/test_http_errors/router_mock.npk
sed -i 's/Server.send_typed/send_typed/g' tests/test_http_errors/router_mock.npk
sed -i '1s/^/use "mock_send_typed.npk".*;\n/' tests/test_http_errors/controllers_mock.npk
sed -i '1s/^/use "mock_send_typed.npk".*;\n/' tests/test_http_errors/router_mock.npk
sed -i 's/send_typed(client_fd\(.*\));/drop(send_typed(client_fd\1));/g' tests/test_http_errors/router_mock.npk
sed -i 's/use "..\/document/use "..\/..\/src\/document/g' tests/test_http_errors/controllers_mock.npk
sed -i 's/use "..\/engine/use "..\/..\/src\/engine/g' tests/test_http_errors/controllers_mock.npk
sed -i 's/use "..\/util/use "..\/..\/src\/util/g' tests/test_http_errors/controllers_mock.npk
sed -i 's/use "..\/index/use "..\/..\/src\/index/g' tests/test_http_errors/controllers_mock.npk
sed -i 's/use "..\/storage/use "..\/..\/src\/storage/g' tests/test_http_errors/controllers_mock.npk
sed -i 's/use "..\/query/use "..\/..\/src\/query/g' tests/test_http_errors/controllers_mock.npk
sed -i 's/use "..\/vector/use "..\/..\/src\/vector/g' tests/test_http_errors/controllers_mock.npk
sed -i 's/use "errors.npk"/use "..\/..\/src\/network\/errors.npk"/g' tests/test_http_errors/controllers_mock.npk
sed -i 's/use "errors_mock.npk"/use "..\/..\/src\/network\/errors.npk"/g' tests/test_http_errors/controllers_mock.npk
sed -i 's/use "rwlock.npk"/use "..\/..\/src\/network\/rwlock.npk"/g' tests/test_http_errors/controllers_mock.npk
sed -i 's/use "atomic.npk"/use "..\/..\/src\/network\/atomic.npk"/g' tests/test_http_errors/controllers_mock.npk

sed -i 's/use "..\/util/use "..\/..\/src\/util/g' tests/test_http_errors/router_mock.npk
sed -i 's/use "errors.npk"/use "..\/..\/src\/network\/errors.npk"/g' tests/test_http_errors/router_mock.npk
sed -i 's/use "errors_mock.npk"/use "..\/..\/src\/network\/errors.npk"/g' tests/test_http_errors/router_mock.npk
sed -i 's/use "rwlock.npk"/use "..\/..\/src\/network\/rwlock.npk"/g' tests/test_http_errors/router_mock.npk
sed -i 's/use "atomic.npk"/use "..\/..\/src\/network\/atomic.npk"/g' tests/test_http_errors/router_mock.npk
sed -i 's/"controllers.npk"/"controllers_mock.npk"/g' tests/test_http_errors/router_mock.npk

# Add mock send_typed

# Fix relative path imports

# Route to our local mocks
sed -i 's/"controllers.npk".*/"controllers_mock.npk".*;/g' tests/test_http_errors/router_mock.npk

# We also need to mock `errors.npk` references if controllers use it! Wait, controllers need to use format_error_json!

/home/randy/Workspace/REPOS/nitpick/build/npkc tests/test_http_errors/main.npk -o tests/test_http_errors/main_bin
./tests/test_http_errors/main_bin
echo "=== Done ==="
