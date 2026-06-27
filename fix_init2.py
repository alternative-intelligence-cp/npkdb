with open('tests/test_api_endpoints/main.npk', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "body_ptr: r2_ptr," in line:
        lines[i] = "        body_ptr: 0i64,\n"
    if "drop(route_request(2i64, r2, 0i64));" in line:
        lines[i] = "    r2.body_ptr = r2_ptr;\n    drop(route_request(2i64, r2, 0i64));\n"
    if "body_ptr: r3_ptr," in line:
        lines[i] = "        body_ptr: 0i64,\n"
    if "drop(route_request(3i64, r3, 0i64));" in line:
        lines[i] = "    r3.body_ptr = r3_ptr;\n    drop(route_request(3i64, r3, 0i64));\n"

with open('tests/test_api_endpoints/main.npk', 'w') as f:
    f.writelines(lines)
