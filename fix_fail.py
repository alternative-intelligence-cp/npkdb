import re
filepath = 'tests/test_distance_props/main.npk'
with open(filepath, 'r') as f:
    content = f.read()

content = re.sub(r'exit \d+i32;', r'fail(1i32);', content)

with open(filepath, 'w') as f:
    f.write(content)
