import glob
import re

files = glob.glob('src/storage/*.npk') + glob.glob('tests/test_integration/*.npk')
for f in files:
    with open(f, 'r') as fp:
        lines = fp.readlines()
    
    new_lines = []
    for line in lines:
        # replace `var = func(...) ? fallback;` with `var = raw func(...);`
        line = re.sub(r'([a-zA-Z0-9_]+\s*=\s*)([a-zA-Z0-9_]+\([^\n;]*?\))\s*\?\s*[^\n;]+;', r'\1raw \2;', line)
        # replace `func(...) ? fallback;` with `raw func(...);` when it's just a drop or call
        line = re.sub(r'(drop\()([a-zA-Z0-9_]+\([^\n;]*?\))\s*\?\s*[^\n;]+?(\);)', r'\1raw \2\3', line)
        line = re.sub(r'(pass\()([a-zA-Z0-9_]+\([^\n;]*?\))\s*\?\s*[^\n;]+?(\);)', r'\1raw \2\3', line)
        new_lines.append(line)
        
    with open(f, 'w') as fp:
        fp.writelines(new_lines)
