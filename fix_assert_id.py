import re
with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

bad_assert = """func:assert = NIL(bool:cond, int32:id) {
    if (cond == false) {
        exit id;
    }
    pass(NIL);
};"""

good_assert = """pub func:failsafe = int32(int32:err) {
    exit err;
};

func:assert = NIL(bool:cond, int32:id) {
    if (cond == false) {
        drop(failsafe(id));
    }
    pass(NIL);
};"""

code = code.replace(bad_assert, good_assert)

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
