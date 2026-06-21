import re
with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

# I currently have a_ptr and b_ptr freed manually? NO, my previous inline_assert.py FAILED to compile because of "Memory leak on early exit".
# This means I have `drop(my_free(a_ptr))` at the END of the scope, but NO `defer`!
# Let's replace `wild tfp64->:a_ptr = raw my_calloc(...);` with `... defer { drop(my_free(a_ptr)); }`
code = re.sub(r'wild tfp64->:a_ptr = raw my_calloc\(([^)]+)\);', r'wild tfp64->:a_ptr = raw my_calloc(\1);\n        defer { drop(my_free(a_ptr)); }', code)
code = re.sub(r'wild tfp64->:b_ptr = raw my_calloc\(([^)]+)\);', r'wild tfp64->:b_ptr = raw my_calloc(\1);\n        defer { drop(my_free(b_ptr)); }', code)

# And remove the manual drop(my_free(a_ptr)) at the end of blocks
code = re.sub(r'drop\(my_free\([ab]_ptr\)\);\n\s*', '', code)

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
