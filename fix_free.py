import os

dirs = [
    "/home/randy/Workspace/REPOS/npkdb/src/main.npk",
    "/home/randy/Workspace/REPOS/npkdb/tests/test_http_core/main.npk",
    "/home/randy/Workspace/REPOS/npkdb/tests/test_http_errors/controllers_mock.npk",
    "/home/randy/Workspace/REPOS/npkdb/tests/test_api_endpoints/controllers_mock.npk"
]

for path in dirs:
    if os.path.exists(path):
        with open(path, "r") as f:
            code = f.read()
        code = code.replace("free(", "npk_core_dalloc(")
        with open(path, "w") as f:
            f.write(code)
        print(f"Fixed {path}")
