import re
with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

# remove func:assert
code = re.sub(r'func:assert = NIL\(bool:cond, int32:id\) \{.*?pass\(NIL\);\n};', '', code, flags=re.DOTALL)

# replace assert(X, Y) with if (X == false) { exit Y; }
code = re.sub(r'assert\(([^,]+), (\d+)i32\);', r'if ((\1) == false) { exit \2i32; }', code)

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
