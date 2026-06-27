import os
import glob
import re

for filepath in glob.glob('tests/**/*.npk', recursive=True):
    with open(filepath, 'r') as f:
        content = f.read()

    content = re.sub(r'\bwild\s+([A-Za-z0-9_]+->)', r'\1', content)
    content = re.sub(r'(?<!@)\bcast_unchecked<([A-Za-z0-9_]+->)>', r'@cast_unchecked<\1>', content)

    with open(filepath, 'w') as f:
        f.write(content)

print("Done fixing wild pointers in all npkdb tests.")
