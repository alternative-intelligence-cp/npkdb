import re
filepath = 'tests/test_distance_props/main.npk'
with open(filepath, 'r') as f:
    content = f.read()

content = content.replace('fail(2i32)', 'fail(53i32)')

with open(filepath, 'w') as f:
    f.write(content)
