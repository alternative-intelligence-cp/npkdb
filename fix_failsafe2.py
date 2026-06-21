with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

bad_failsafe = """pub func:failsafe = int32(int32:err) {
    exit err;
};

func:assert = NIL(bool:cond, int32:id) {
    if (cond == false) {
        drop(failsafe(id));
    }
    pass(NIL);
};"""

good_failsafe = """pub func:failsafe = int32(tbb32:err) {
    exit @cast_unchecked<int32>(err);
};

func:assert = NIL(bool:cond, int32:id) {
    if (cond == false) {
        drop(failsafe(@cast_unchecked<tbb32>(id)));
    }
    pass(NIL);
};"""

code = code.replace(bad_failsafe, good_failsafe)

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
