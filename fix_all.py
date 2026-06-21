with open("tests/test_distance/main.npk", "r") as f:
    lines = f.readlines()

new_lines = []
skip_next = False
for line in lines:
    if "defer {" in line:
        continue
    if "drop(my_free(" in line:
        continue
    new_lines.append(line)

code = "".join(new_lines)

# Now, we know each test block ends with `}`.
# We will insert `drop(my_free(a_ptr)); drop(my_free(b_ptr));` before every `}` that is indented by 4 spaces.
import re
code = re.sub(r'( {4})\}', r'\1    drop(my_free(a_ptr));\n\1    drop(my_free(b_ptr));\n\1}', code)

# Let's fix assert
code = re.sub(r'if \(\(([^)]+)\) == false\) \{ exit \d+i32; \}', r'assert(\1);', code)
code = re.sub(r'if \(([^ ]+) == false\) \{ exit \d+i32; \}', r'assert(\1);', code)

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)

