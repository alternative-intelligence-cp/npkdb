with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

bad_failsafe = """pub func:failsafe = int32(tbb32:err) {
    drop(failsafe(@cast_unchecked<tbb32>(1i32)));
};"""

good_failsafe = """pub func:failsafe = int32(tbb32:err) {
    exit 1i32;
};"""

code = code.replace(bad_failsafe, good_failsafe)

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
