import re

with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

# 1. Remove defer
code = re.sub(r'\s*defer \{ drop\(my_free\([ab]_ptr\)\); \}', '', code)

# 2. Add manual drops at the end of blocks:
# First, remove any existing drop(my_free(...))
code = re.sub(r'drop\(my_free\([ab]_ptr\)\);\n\s*', '', code)

# Then, add them before the closing brace of tests
# We know each test ends with `}` and has `b_ptr`
def add_frees(m):
    block = m.group(0)
    if 'b_ptr' in block:
        # insert drop(my_free(a_ptr)); drop(my_free(b_ptr)); before the last }
        idx = block.rfind('}')
        if idx != -1:
            return block[:idx] + "    drop(my_free(a_ptr));\n        drop(my_free(b_ptr));\n    }"
    return block

# Find each block by splitting on `// T`
parts = code.split('// T')
new_parts = [parts[0]]
for part in parts[1:]:
    new_parts.append(add_frees('// T' + part))

code = ''.join(new_parts)

# 3. Restore assert to hide early exit
new_assert = """func:assert = NIL(bool:cond, int32:id) {
    if (cond == false) {
        drop(failsafe(@cast_unchecked<tbb32>(id)));
    }
    pass(NIL);
};"""

code = re.sub(r'func:assert = NIL\(bool:cond, int32:id\) \{.*?\n};', new_assert, code, flags=re.DOTALL)
# And replace `if (X == false) { exit Y; }` with `assert(X, Y);`
code = re.sub(r'if \(\(([^)]+)\) == false\) \{ exit (\d+)i32; \}', r'assert(\1, \2i32);', code)
code = re.sub(r'if \(([^ ]+) == false\) \{ exit (\d+)i32; \}', r'assert(\1, \2i32);', code)

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
