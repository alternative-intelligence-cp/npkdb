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
sed -i 's/raw Server.send_typed/send_typed/g' tests/test_http_errors/router_mock.npk

# Add mock send_typed
sed -i '1s/^/pub func:send_typed = int64(int64:fd, int64:code, string:ct, string:body);\n/' tests/test_http_errors/controllers_mock.npk
sed -i '1s/^/pub func:send_typed = int64(int64:fd, int64:code, string:ct, string:body);\n/' tests/test_http_errors/router_mock.npk

# Fix relative path imports
sed -i 's/\.\.\/util/\.\.\/\.\.\/src\/util/g' tests/test_http_errors/controllers_mock.npk
sed -i 's/\.\.\/util/\.\.\/\.\.\/src\/util/g' tests/test_http_errors/router_mock.npk
sed -i 's/\.\.\/util/\.\.\/\.\.\/src\/util/g' tests/test_http_errors/errors_mock.npk || true
sed -i 's/\.\.\/document/\.\.\/\.\.\/src\/document/g' tests/test_http_errors/controllers_mock.npk

# Route to our local mocks
sed -i 's/"controllers.npk".*/"controllers_mock.npk".*;/g' tests/test_http_errors/router_mock.npk
sed -i 's/..\/..\/src\/network\/router.npk/router_mock.npk/g' tests/test_http_errors/main.npk

# We also need to mock `errors.npk` references if controllers use it! Wait, controllers need to use format_error_json!
sed -i 's/"errors.npk".*/"errors_mock.npk".*;/g' tests/test_http_errors/controllers_mock.npk
sed -i 's/"errors.npk".*/"errors_mock.npk".*;/g' tests/test_http_errors/router_mock.npk || true

/home/randy/Workspace/REPOS/nitpick/build/npkc tests/test_http_errors/main.npk -o tests/test_http_errors/main_bin
./tests/test_http_errors/main_bin
echo "=== Done ==="
