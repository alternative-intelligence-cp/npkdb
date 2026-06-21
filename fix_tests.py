import re

with open("tests/test_distance/main.npk", "r") as f:
    code = f.read()

# Replace assert(...) == literal
code = re.sub(r'assert\(@cast_unchecked<tfp64>\(res_val\) == 0\.0tf\);', 'drop(assert_eq(res_val, EXPECTED_0));', code)
code = re.sub(r'assert\(@cast_unchecked<tfp64>\(res_val\) == 1\.0tf\);', 'drop(assert_eq(res_val, EXPECTED_1));', code)
code = re.sub(r'assert\(@cast_unchecked<tfp64>\(res_val\) == -1\.0tf\);', 'drop(assert_eq(res_val, EXPECTED_N1));', code)
code = re.sub(r'assert\(@cast_unchecked<tfp64>\(res_val\) == 2\.0tf\);', 'drop(assert_eq(res_val, EXPECTED_2));', code)
code = re.sub(r'assert\(@cast_unchecked<tfp64>\(res_val\) == 4\.0tf\);', 'drop(assert_eq(res_val, EXPECTED_4));', code)
code = re.sub(r'assert\(@cast_unchecked<tfp64>\(res_val\) == 15\.0tf\);', 'drop(assert_eq(res_val, EXPECTED_15));', code)
code = re.sub(r'assert\(@cast_unchecked<tfp64>\(res_val\) == 1536\.0tf\);', 'drop(assert_eq(res_val, EXPECTED_1536));', code)

code = re.sub(r'assert\(res_val == 0\.0tf\);', 'drop(assert_eq(res_val, EXPECTED_0));', code)
code = re.sub(r'assert\(res_val == 1\.0tf\);', 'drop(assert_eq(res_val, EXPECTED_1));', code)
code = re.sub(r'assert\(res_val == -1\.0tf\);', 'drop(assert_eq(res_val, EXPECTED_N1));', code)
code = re.sub(r'assert\(res_val == 2\.0tf\);', 'drop(assert_eq(res_val, EXPECTED_2));', code)
code = re.sub(r'assert\(res_val == 4\.0tf\);', 'drop(assert_eq(res_val, EXPECTED_4));', code)
code = re.sub(r'assert\(res_val == 15\.0tf\);', 'drop(assert_eq(res_val, EXPECTED_15));', code)
code = re.sub(r'assert\(res_val == 1536\.0tf\);', 'drop(assert_eq(res_val, EXPECTED_1536));', code)

# Replace assert(...) < literal
code = re.sub(r'assert\(@cast_unchecked<tfp64>\(diff\) < 1e-10tf\);', 'drop(assert_lt(diff, EPSILON));', code)
code = re.sub(r'assert\(diff < 1e-10tf\);', 'drop(assert_lt(diff, EPSILON));', code)

# Replace diff = res_val - literal
code = re.sub(r'tfp64:diff = res_val - 0\.0tf;', 'tfp64:diff = res_val - EXPECTED_0;', code)
code = re.sub(r'tfp64:diff = res_val - 1\.0tf;', 'tfp64:diff = res_val - EXPECTED_1;', code)
code = re.sub(r'tfp64:diff = res_val - \(-1\.0tf\);', 'tfp64:diff = res_val - EXPECTED_N1;', code)

# Replace if (diff < 0.0tf)
code = re.sub(r'if \(diff < 0\.0tf\) \{ diff = 0\.0tf - diff; \}', 'if (diff < EXPECTED_0) { diff = EXPECTED_0 - diff; }', code)

with open("tests/test_distance/main.npk", "w") as f:
    f.write(code)
