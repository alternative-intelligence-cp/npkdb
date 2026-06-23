#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== NPKDB v0.3.9 — API Endpoints ==="
cd "${REPO_ROOT}"
mkdir -p tests/test_api_endpoints

# Notice we sed out the Server.send_typed in controllers.npk for testing since we mocked it
cp src/network/controllers.npk tests/test_api_endpoints/controllers_mock.npk
cp src/network/router.npk tests/test_api_endpoints/router_mock.npk

sed -i 's/raw Server.send_typed/send_typed/g' tests/test_api_endpoints/controllers_mock.npk
sed -i 's/raw Server.send_typed/send_typed/g' tests/test_api_endpoints/router_mock.npk
sed -i '1s/^/pub func:send_typed = int64(int64:fd, int64:code, string:ct, string:body);\n/' tests/test_api_endpoints/controllers_mock.npk
sed -i '1s/^/pub func:send_typed = int64(int64:fd, int64:code, string:ct, string:body);\n/' tests/test_api_endpoints/router_mock.npk
sed -i 's/use "..\/document/use "..\/..\/src\/document/g' tests/test_api_endpoints/controllers_mock.npk
sed -i 's/use "..\/util/use "..\/..\/src\/util/g' tests/test_api_endpoints/controllers_mock.npk
sed -i 's/use "..\/index/use "..\/..\/src\/index/g' tests/test_api_endpoints/controllers_mock.npk
sed -i 's/use "..\/storage/use "..\/..\/src\/storage/g' tests/test_api_endpoints/controllers_mock.npk
sed -i 's/use "..\/query/use "..\/..\/src\/query/g' tests/test_api_endpoints/controllers_mock.npk
sed -i 's/use "..\/vector/use "..\/..\/src\/vector/g' tests/test_api_endpoints/controllers_mock.npk
sed -i 's/use "errors.npk"/use "..\/..\/src\/network\/errors.npk"/g' tests/test_api_endpoints/controllers_mock.npk
sed -i 's/use "errors_mock.npk"/use "..\/..\/src\/network\/errors.npk"/g' tests/test_api_endpoints/controllers_mock.npk
sed -i 's/use "rwlock.npk"/use "..\/..\/src\/network\/rwlock.npk"/g' tests/test_api_endpoints/controllers_mock.npk
sed -i 's/use "atomic.npk"/use "..\/..\/src\/network\/atomic.npk"/g' tests/test_api_endpoints/controllers_mock.npk
sed -i 's/use "..\/..\/..\/nitpick\/stdlib/use "..\/..\/..\/..\/nitpick\/stdlib/g' tests/test_api_endpoints/controllers_mock.npk
sed -i 's/use "..\/util/use "..\/..\/src\/util/g' tests/test_api_endpoints/router_mock.npk
sed -i 's/use "errors.npk"/use "..\/..\/src\/network\/errors.npk"/g' tests/test_api_endpoints/router_mock.npk
sed -i 's/use "errors_mock.npk"/use "..\/..\/src\/network\/errors.npk"/g' tests/test_api_endpoints/router_mock.npk
sed -i 's/use "rwlock.npk"/use "..\/..\/src\/network\/rwlock.npk"/g' tests/test_api_endpoints/router_mock.npk
sed -i 's/use "atomic.npk"/use "..\/..\/src\/network\/atomic.npk"/g' tests/test_api_endpoints/router_mock.npk
sed -i 's/"controllers.npk"/"controllers_mock.npk"/g' tests/test_api_endpoints/router_mock.npk
sed -i 's/"controllers.npk".*/"controllers_mock.npk".*;/g' tests/test_api_endpoints/router_mock.npk

/home/randy/Workspace/REPOS/nitpick/build/npkc tests/test_api_endpoints/main.npk -o tests/test_api_endpoints/main_bin
./tests/test_api_endpoints/main_bin
echo "=== Done ==="
