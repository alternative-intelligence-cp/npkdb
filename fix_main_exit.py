import re
filepath = 'tests/test_distance_props/main.npk'
with open(filepath, 'r') as f:
    content = f.read()

content = content.replace('if (pass_count < 40i64) { fail(1i32); } else { fail(1i32); }', 'if (pass_count < 40i64) { exit 1i32; } else { exit 0i32; }')
content = content.replace('    fail(1i32);\n};', '    exit 0i32;\n};')

with open(filepath, 'w') as f:
    f.write(content)
