import glob
import re

files = glob.glob('src/storage/*.npk') + glob.glob('tests/test_integration/*.npk')
for f in files:
    with open(f, 'r') as fp:
        code = fp.read()
    
    code = code.replace('? 123456789i64', '?! 123456789i64')
    code = code.replace('? 1i64', '?! 1i64')
    
    with open(f, 'w') as fp:
        fp.write(code)
