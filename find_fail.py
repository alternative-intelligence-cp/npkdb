with open("tests/test_distance/main.npk", "r") as f:
    lines = f.readlines()

new_lines = []
test_count = 1
for line in lines:
    if "drop(assert_" in line or "assert(" in line:
        line = line.replace("drop(failsafe(@cast_unchecked<tbb32>(1i32)));", f"exit {test_count}i32;")
        if "assert(res.is_error)" in line or "assert(err != NIL)" in line:
            line = line.replace("assert(", f"if (")
            line = line.replace(");", f" == false) {{ exit {test_count}i32; }}")
        test_count += 1
    new_lines.append(line)

with open("tests/test_distance/main.npk", "w") as f:
    f.writelines(new_lines)
