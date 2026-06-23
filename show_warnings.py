import subprocess
import json
import re

with open("build/line_map.json", "r") as fp:
    line_map = json.load(fp)

cmd = "export PATH=\"/home/randy/Workspace/REPOS/nitpick/build:$PATH\" && npkc build/flattened.npk -c 2>&1"
res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
output = re.sub(r'\x1B\[[0-9;]*[mK]', '', res.stdout)

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
    elif "warning: Variable " in line:
        # these don't have line numbers in the first part sometimes, but wait:
        # src/main.npk:0:0: warning: Variable 'j' shadows outer declaration at line 200, column 9 (original at line 189, column 5)
        # We can map the "at line 200" and "at line 189"
        m = re.search(r'shadows outer declaration at line (\d+).*original at line (\d+)', line)
        if m:
            flat_line = int(m.group(1))
            orig_line_inner = int(m.group(2))
            orig1 = line_map.get(str(flat_line))
            orig2 = line_map.get(str(orig_line_inner))
            if orig1 and orig2:
                warnings.append(f"SHADOW: {orig1[0]}:{orig1[1]} shadows {orig2[0]}:{orig2[1]} ({line})")
            else:
                warnings.append(f"SHADOW: {line}")

for w in warnings:
    print(w)
print(f"Total Warnings: {len(warnings)}")
