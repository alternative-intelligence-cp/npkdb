import re

errors_file = "errors.txt"

with open(errors_file, "r") as fp:
    errors = fp.read().splitlines()

fixes = {}
for err in errors:
    m = re.match(r'([^:]+):(\d+) - (.*)', err)
    if m:
        file = m.group(1)
        line = int(m.group(2))
        msg = m.group(3)
        if file not in fixes:
            fixes[file] = []
        fixes[file].append((line, msg))

for file, items in fixes.items():
    with open(file, "r") as fp:
        content = fp.readlines()

    # Apply fixes in reverse line order to avoid messing up indices? No, we just replace in place
    for line_num, msg in items:
        idx = line_num - 1
        code = content[idx]
        
        if "Cannot silently unwrap Result" in msg:
            if "=" in code and "raw " not in code:
                # Add raw after the =
                parts = code.split("=", 1)
                content[idx] = parts[0] + "= raw " + parts[1].lstrip()
            elif "return" in code and "raw " not in code:
                content[idx] = code.replace("return ", "return raw ")
            elif "pass(" in code and "raw " not in code:
                content[idx] = code.replace("pass(", "pass(raw ")
        elif "has no member 'err'" in msg:
            content[idx] = code.replace(".err", ".error")
        elif "Logical NOT requires 'bool' type" in msg:
            if "if (!" in code:
                content[idx] = code.replace("if (!", "if (").replace(")", ".is_error)")
                # This could be buggy if there are multiple parens, let's use regex
                # Actually, most are `if (!foo) {`, so let's do:
                content[idx] = re.sub(r'if \(!([a-zA-Z0-9_]+)\)', r'if (\1.is_error)', code)

    with open(file, "w") as fp:
        fp.writelines(content)

print("Applied fixes based on errors.txt")
