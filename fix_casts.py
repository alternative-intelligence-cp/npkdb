import os
import re
import glob

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Pattern 1: (expr) => type
    content = re.sub(r'\(([^()=>]+)\)\s*=>\s*(\w+)', r'@cast_unchecked<\2>(\1)', content)
    
    # Pattern 2: var => type
    content = re.sub(r'([\w_]+)\s*=>\s*(\w+)', r'@cast_unchecked<\2>(\1)', content)
    
    with open(filepath, 'w') as f:
        f.write(content)

for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith('.npk'):
            fix_file(os.path.join(root, file))

for root, dirs, files in os.walk('tests'):
    for file in files:
        if file.endswith('.npk'):
            fix_file(os.path.join(root, file))

print("Fixed casts!")
