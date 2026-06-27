with open('tests/test_api_endpoints/main.npk', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "body_ptr: raw make_r2_buf()," in line:
        lines[i] = "        body_ptr: r2_ptr,\n"
    if "ServerRequest:r2 = ServerRequest{" in line:
        lines[i] = "    int64:r2_ptr = raw make_r2_buf();\n    ServerRequest:r2 = ServerRequest{\n"
    if "body_ptr: raw make_r3_buf()," in line:
        lines[i] = "        body_ptr: r3_ptr,\n"
    if "ServerRequest:r3 = ServerRequest{" in line:
        lines[i] = "    int64:r3_ptr = raw make_r3_buf();\n    ServerRequest:r3 = ServerRequest{\n"

with open('tests/test_api_endpoints/main.npk', 'w') as f:
    f.writelines(lines)
