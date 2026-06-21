import re
with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

def repl(m):
    id_val = int(m.group(1))
    return f", {id_val+100}i32)"

code = re.sub(r', (\d+)i32\)', repl, code)

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
