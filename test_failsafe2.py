import re
filepath = 'tests/test_distance_props/main.npk'
with open(filepath, 'r') as f:
    content = f.read()

content = content.replace('exit 0i32;\n};', 'exit 51i32;\n};')

with open(filepath, 'w') as f:
    f.write(content)
