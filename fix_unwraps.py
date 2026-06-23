import re

errors_file = "errors.txt"

with open(errors_file, "r") as fp:
    errors = fp.read().splitlines()

fixes = {}
for err in errors:
    if "Cannot silently unwrap Result" in err:
        m = re.match(r'([^:]+):(\d+) - ', err)
        if m:
            file = m.group(1)
            line = int(m.group(2))
            if file not in fixes:
                fixes[file] = []
            fixes[file].append(line)

for file, lines in fixes.items():
    with open(file, "r") as fp:
        content = fp.readlines()
        
    for line in lines:
        idx = line - 1
        # Insert raw after =
        code = content[idx]
        if "=" in code and "raw " not in code:
            code = code.replace("=", "= raw", 1)
            content[idx] = code
            
    with open(file, "w") as fp:
        fp.writelines(content)
        
print("Fixed unwraps")
