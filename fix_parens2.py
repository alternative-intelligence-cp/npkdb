import os
import re

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # (func(arg1, arg2 => type)) -> (func(arg1, arg2) => type)
    # This specifically targets cases like: (npk_mem_read_int64(node_buf, 0i64 => int32))
    content = re.sub(r'(\w+)\(([^,]+),\s*([^()=>]+)\s*=>\s*(\w+)\)\)', r'(\1(\2, \3) => \4)', content)
    
    # What about func(arg1 => type) ?
    # like (floor(l_val => int32)) -> (floor(l_val) => int32)
    content = re.sub(r'(\w+)\(([^,()=>]+)\s*=>\s*(\w+)\)\)', r'(\1(\2) => \3)', content)

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

print("Fixed parens 2!")
