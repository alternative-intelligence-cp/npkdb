import re

with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

# Make assert take an ID
new_assert = """func:assert = NIL(bool:cond, int32:id) {
    if (cond == false) {
        exit id;
    }
    pass(NIL);
};"""

code = re.sub(r'func:assert = NIL\(bool:cond\) \{.*?};', new_assert, code, flags=re.DOTALL)

# Remove failsafe
code = re.sub(r'pub func:failsafe.*?};', '', code, flags=re.DOTALL)

# Replace all assert(...) with assert(..., id)
count = 1
def replace_assert(match):
    global count
    res = f"assert({match.group(1)}, {count}i32)"
    count += 1
    return res

code = re.sub(r'assert\(([^,]+?)\)', replace_assert, code)

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
