import json
import re

with open("build/line_map.json", "r") as fp:
    line_map = json.load(fp)

with open("real_errors.txt", "r") as fp:
    output = fp.read()

output = re.sub(r'\x1B\[[0-9;]*[mK]', '', output)

warnings = []
for line in output.split("\n"):
    if "warning: Line " in line:
        m = re.search(r'warning: Line (\d+), Column (\d+): (.*)', line)
        if m:
            flat_line = int(m.group(1))
            msg = m.group(3)
            orig = line_map.get(str(flat_line))
            if orig:
                filename, orig_line = orig
                warnings.append(f"{filename}:{orig_line} - {msg}")
            else:
                warnings.append(f"UNKNOWN:{flat_line} - {msg}")
        else:
            warnings.append(f"UNPARSED: {line}")
    elif "warning: Variable " in line and "shadows" in line:
        m = re.search(r'shadows outer declaration at line (\d+).*original at line (\d+)', line)
        if m:
            flat_line = int(m.group(1))
            orig_line_inner = int(m.group(2))
            orig1 = line_map.get(str(flat_line))
            orig2 = line_map.get(str(orig_line_inner))
            if orig1 and orig2:
                warnings.append(f"SHADOW: {orig1[0]}:{orig1[1]} shadows {orig2[0]}:{orig2[1]}")
            else:
                warnings.append(f"SHADOW UNMAPPED: {line}")
        else:
            warnings.append(f"SHADOW OTHER: {line}")
            
    elif "warning: [unused-parameter]" in line:
        warnings.append(line)

with open("mapped_warnings.txt", "w") as fp:
    for w in warnings:
        fp.write(w + "\n")
print(f"Mapped {len(warnings)} warnings to mapped_warnings.txt")
