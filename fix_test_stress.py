import re
with open('tests/test_integration/test_stress.npk', 'r') as f:
    code = f.read()
code = re.sub(r'\s*\?\s*0i64', '', code)
code = re.sub(r'\s*\?\s*""', '', code)
with open('tests/test_integration/test_stress.npk', 'w') as f:
    f.write(code)
