import re

with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

# 1. replace `defer {  }` with nothing
code = re.sub(r'\s*defer \{  \}', '', code)

# 2. at the end of each block `}`, add my_free if there were allocations
def replacer(match):
    block = match.group(0)
    if "a_ptr" in block and "b_ptr" in block:
        # insert drop(my_free(...)) before the closing brace
        return block[:-1] + "    drop(my_free(a_ptr));\n        drop(my_free(b_ptr));\n    }"
    return block

# Find all blocks: { ... }
# Actually just replace `assert(...); \n }` with `assert(...); drop(my_free(a_ptr)); drop(my_free(b_ptr)); }`
code = re.sub(r'(assert\([^;]+;\s*)\}', r'\1    drop(my_free(a_ptr));\n        drop(my_free(b_ptr));\n    }', code)

# For tests 24 and 25 which end differently:
code = re.sub(r'(assert\(err != NIL\);\s*)\}', r'\1    drop(my_free(a_ptr));\n        drop(my_free(b_ptr));\n    }', code)

# 3. restore exit 0i32 at the end of main
code = code.replace("drop(failsafe(@cast_unchecked<tbb32>(1i32)));\n};", "exit 0i32;\n};")

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
