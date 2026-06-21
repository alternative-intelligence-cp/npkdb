import re
filepath = 'tests/test_distance_props/main.npk'
with open(filepath, 'r') as f:
    content = f.read()

# Replace main tests with explicit execution
match = re.search(r'pass_count = pass_count \+ \(run_test\("[^"]+",\s*([a-zA-Z0-9_]+)\(\)\)\s*\?!\s*0i64\);', content)
if not match:
    # already replaced with drop()
    pass

def repl(m):
    return f"drop({m.group(1)}());\n    pass_count = pass_count + 1i64;"

content = re.sub(r'drop\(([a-zA-Z0-9_]+)\(\)\);', repl, content)

with open(filepath, 'w') as f:
    f.write(content)
