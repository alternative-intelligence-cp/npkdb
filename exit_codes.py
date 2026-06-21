import re
filepath = 'tests/test_distance_props/main.npk'
with open(filepath, 'r') as f:
    content = f.read()

count = 101
def repl(m):
    global count
    res = f"exit {count}i32;"
    count += 1
    return res

content = re.sub(r'fail\(1i32\);', repl, content)

with open(filepath, 'w') as f:
    f.write(content)
