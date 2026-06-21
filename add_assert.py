with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

assert_code = """func:assert_eq = NIL(tfp64:actual, tfp64:expected) {
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
};

func:assert = NIL(bool:cond) {
    if (cond == false) {
        drop(failsafe(@cast_unchecked<tbb32>(1i32)));
    }
    pass(NIL);
};"""

code = code.replace("""func:assert_eq = NIL(tfp64:actual, tfp64:expected) {
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
};""", assert_code)

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
