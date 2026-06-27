import re
with open('tests/test_integration/test_stress.npk', 'r') as fp:
    code = fp.read()
code = code.replace('drop(wp_put(wp1, k, v_ptr, 28i64)); // 28 chars long', 'println("Put " + k); drop(wp_put(wp1, k, v_ptr, 28i64));')
code = code.replace('string:vtest = db_get(wp1, "stress_key_000463")', 'println("db_get..."); string:vtest = db_get(wp1, "stress_key_000463")')
with open('tests/test_integration/test_stress.npk', 'w') as fp:
    fp.write(code)
