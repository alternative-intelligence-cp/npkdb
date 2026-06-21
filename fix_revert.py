import os
import re

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Pattern: @cast_unchecked<type>(expr) -> (expr => type)
    # Be careful with parentheses
    content = re.sub(r'@cast_unchecked<([A-Za-z0-9_]+)>\(([^)]+)\)', r'(\2 => \1)', content)

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

print("Reverted casts!")
