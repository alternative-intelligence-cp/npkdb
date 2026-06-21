import re

with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

# I messed up the file a lot. Let's try to restore it by undoing all my changes!

# 1. remove assert_eq and assert_lt
code = re.sub(r'func:assert_eq = NIL.*?};', '', code, flags=re.DOTALL)
code = re.sub(r'func:assert_lt = NIL.*?};', '', code, flags=re.DOTALL)

# 2. replace drop(assert_eq(...)) with assert(...) == ...
# drop(assert_eq(res_val, EXPECTED_0)); -> assert(@cast_unchecked<tfp64>(res_val) == EXPECTED_0);
code = re.sub(r'drop\(assert_eq\((res_val), (EXPECTED_[^\)]+)\)\);', r'assert(@cast_unchecked<tfp64>(\1) == \2);', code)

# drop(assert_lt(diff, EPSILON)); -> assert(@cast_unchecked<tfp64>(diff) < EPSILON);
code = re.sub(r'drop\(assert_lt\((diff), (EPSILON)\)\);', r'assert(@cast_unchecked<tfp64>(\1) < \2);', code)

# 3. clean up double frees
code = re.sub(r'(drop\(my_free\([ab]_ptr\)\);\n\s*)+', r'', code)

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
