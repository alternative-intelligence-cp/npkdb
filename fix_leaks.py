with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

# We need to make sure every block has drop(my_free(a_ptr)); drop(my_free(b_ptr)); before exiting!
# But since I used exit, the NLL checker complained.
# What if I change assert_eq back to:
new_assert_eq = """func:assert_eq = NIL(tfp64:actual, tfp64:expected) {
    if (actual == expected) {
        pass(NIL);
    } else {
        drop(failsafe(@cast_unchecked<tbb32>(1i32)));
        pass(NIL);
    }
};"""

new_assert_lt = """func:assert_lt = NIL(tfp64:actual, tfp64:expected) {
    if (actual < expected) {
        pass(NIL);
    } else {
        drop(failsafe(@cast_unchecked<tbb32>(1i32)));
        pass(NIL);
    }
};"""

import re
code = re.sub(r'func:assert_eq.*?};', new_assert_eq, code, flags=re.DOTALL)
code = re.sub(r'func:assert_lt.*?};', new_assert_lt, code, flags=re.DOTALL)

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
