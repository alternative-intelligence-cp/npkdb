import subprocess
import json
import re

with open("build/line_map.json", "r") as fp:
    line_map = json.load(fp)

cmd = "export PATH=\"/home/randy/Workspace/REPOS/nitpick/build:$PATH\" && npkc build/flattened.npk -o build/npkdb 2>&1"
res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
output = re.sub(r'\x1B\[[0-9;]*[mK]', '', res.stdout)

errors = []
for line in output.split("\n"):
    if "error: Line " in line:
        m = re.search(r'error: Line (\d+), Column (\d+): (.*)', line)
        if m:
            flat_line = int(m.group(1))
            msg = m.group(3)
            orig = line_map.get(str(flat_line))
            if orig:
                filename, orig_line = orig
                errors.append(f"{filename}:{orig_line} - {msg}")
            else:
                errors.append(f"UNKNOWN:{flat_line} - {msg}")

for e in errors:
    print(e)
print(f"Total Errors: {len(errors)}")
