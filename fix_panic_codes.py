import glob
import re

files = glob.glob('src/storage/*.npk') + glob.glob('tests/test_integration/*.npk')
for f in files:
    with open(f, 'r') as fp:
        code = fp.read()
    
    code = code.replace('?! ""', '?! 1i64')
    code = code.replace('?! false', '?! 1i64')
    code = code.replace('?! 0.0f', '?! 1i64')
    
    with open(f, 'w') as fp:
        fp.write(code)
