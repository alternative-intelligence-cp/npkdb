import re
filepath = 'tests/test_distance_props/main.npk'
with open(filepath, 'r') as f:
    content = f.read()

content = re.sub(r'run_test\("([^"]+)",\s*([a-zA-Z0-9_]+)\(\)\s*\?!\s*NIL\)\s*\?!\s*0i64', r'run_test("\1", \2()) ?! 0i64', content)

with open(filepath, 'w') as f:
    f.write(content)
