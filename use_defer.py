import re

with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

# Replace allocations with defer
code = re.sub(r'(wild tfp64->:a_ptr = raw my_calloc\([^;]+\);)', r'\1\n        defer { drop(my_free(a_ptr)); }', code)
code = re.sub(r'(wild tfp64->:b_ptr = raw my_calloc\([^;]+\);)', r'\1\n        defer { drop(my_free(b_ptr)); }', code)

# Remove old drop(my_free(...))
code = code.replace("drop(my_free(a_ptr));", "")
code = code.replace("drop(my_free(b_ptr));", "")

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
