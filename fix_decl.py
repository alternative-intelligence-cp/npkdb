with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

# Replace assert function with new ones
old_assert = """func:assert = NIL(bool:cond) {
    if (cond == false) {
        drop(failsafe(@cast_unchecked<tbb32>(1i32)));
    }
    pass(NIL);
};"""

new_assert = """func:assert_eq = NIL(tfp64:actual, tfp64:expected) {
    if (actual == expected) {
        pass(NIL);
    } else {
        drop(failsafe(@cast_unchecked<tbb32>(1i32)));
        pass(NIL);
    }
};

func:assert_lt = NIL(tfp64:actual, tfp64:expected) {
    if (actual < expected) {
        pass(NIL);
    } else {
        drop(failsafe(@cast_unchecked<tbb32>(1i32)));
        pass(NIL);
    }
};"""

code = code.replace(old_assert, new_assert)

# Add variables to start of main
main_start = """pub func:main = int32() {
    int64:passed = 0i64;
    int64:failed = 0i64;"""

new_main_start = """pub func:main = int32() {
    tfp64:EXPECTED_0   = 0.0tf;
    tfp64:EXPECTED_1   = 1.0tf;
    tfp64:EXPECTED_N1  = -1.0tf;
    tfp64:EXPECTED_2   = 2.0tf;
    tfp64:EXPECTED_4   = 4.0tf;
    tfp64:EXPECTED_15  = 15.0tf;
    tfp64:EXPECTED_1536 = 1536.0tf;
    tfp64:EPSILON      = 1e-10tf;
    int64:passed = 0i64;
    int64:failed = 0i64;"""

code = code.replace(main_start, new_main_start)

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
