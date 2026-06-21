import re

with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

# Remove defers
code = re.sub(r'\s*defer \{ drop\(my_free\([ab]_ptr\)\); \}', '', code)

# Put back drop(my_free)
code = re.sub(r'drop\(assert_lt\(diff, EPSILON\)\);', r'drop(assert_lt(diff, EPSILON));\n        drop(my_free(a_ptr));\n        drop(my_free(b_ptr));', code)
code = re.sub(r'drop\(assert_eq\(res_val, EXPECTED_[^\)]+\)\);', r'\g<0>\n        drop(my_free(a_ptr));\n        drop(my_free(b_ptr));', code)

# Fix double frees if any
code = re.sub(r'(drop\(my_free\([ab]_ptr\)\);\n\s*){2,}', r'\1', code)

# Restore drop(failsafe)
code = re.sub(r'exit \d+i32;', r'drop(failsafe(@cast_unchecked<tbb32>(1i32)));', code)

# Restore assert(res.is_error)
code = re.sub(r'if \(res\.is_error == false\) \{ drop\(failsafe\(@cast_unchecked<tbb32>\(1i32\)\)\); \}', r'assert(res.is_error);', code)
code = re.sub(r'if \(err != NIL == false\) \{ drop\(failsafe\(@cast_unchecked<tbb32>\(1i32\)\)\); \}', r'assert(err != NIL);', code)

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
