import os
import re

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Match `(EXPR => TYPE)` where EXPR doesn't contain `=>` or parentheses
    # But EXPR might contain parens...
    # Let's match `(var => type)`
    content = re.sub(r'\(([A-Za-z0-9_]+)\s*=>\s*([A-Za-z0-9_]+)\)', r'@cast_unchecked<\2>(\1)', content)

    # Match `(foo(bar) => type)`
    content = re.sub(r'\(([A-Za-z0-9_]+\([^)]+\))\s*=>\s*([A-Za-z0-9_]+)\)', r'@cast_unchecked<\2>(\1)', content)

    # Match `(foo(bar, baz) => type)`
    content = re.sub(r'\(([A-Za-z0-9_]+\([^)]+,\s*[^)]+\))\s*=>\s*([A-Za-z0-9_]+)\)', r'@cast_unchecked<\2>(\1)', content)
    
    # Match `(foo + bar => type)` etc.
    content = re.sub(r'\(([^()]+)\s*=>\s*([A-Za-z0-9_]+)\)', r'@cast_unchecked<\2>(\1)', content)

    # Let's see if there are any remaining `=>`
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

print("Fixed casts final!")
