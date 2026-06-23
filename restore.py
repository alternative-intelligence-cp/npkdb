import os
import re

with open("/home/randy/.gemini/antigravity-ide/brain/0dfd17ae-e1cb-446d-99e7-351f4487e296/compilation_4.md", "r") as f:
    content = f.read()

# We need to find `## `src/path/to/file.npk``
# and then the ```nitpick block.

pattern = re.compile(r'## `([^`]+)`\s*```[a-z]*\s*(.*?)```', re.DOTALL)
matches = pattern.findall(content)

count = 0
for filename, code in matches:
    if filename.startswith('src/'):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            f.write(code)
        count += 1

print(f"Restored {count} files from compilation_4.md")
