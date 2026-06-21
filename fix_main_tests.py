import re
filepath = 'tests/test_distance_props/main.npk'
with open(filepath, 'r') as f:
    content = f.read()

# Replace all pass_count = pass_count + (run_test("...", tXX_YY_ZZ()) ?! 0i64);
# with drop(tXX_YY_ZZ());

def repl(m):
    return f"drop({m.group(2)}());"

content = re.sub(r'pass_count = pass_count \+ \(run_test\("[^"]+",\s*([a-zA-Z0-9_]+)\(\)\)\s*\?!\s*0i64\);', r'drop(\1());', content)

with open(filepath, 'w') as f:
    f.write(content)
