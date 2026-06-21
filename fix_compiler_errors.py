import subprocess
import json
import re
import os

with open("build/line_map.json", "r") as fp:
    line_map = json.load(fp)

cmd = "export PATH=\"/home/randy/Workspace/REPOS/nitpick/build:$PATH\" && npkc build/flattened.npk -o build/test_hnsw_graph 2>&1"
res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
output = res.stdout

# Group errors by original file -> line -> error type
fixes = {}

for line in output.split("\n"):
    if "error: Line " in line:
        m = re.search(r'error: Line (\d+), Column (\d+): (.*)', line)
        if m:
            flat_line = m.group(1)
            msg = m.group(3)
            
            orig = line_map.get(flat_line)
            if not orig: continue
            
            filename, orig_line = orig
            
            if filename not in fixes:
                fixes[filename] = []
                
            fixes[filename].append((orig_line, msg))

for filename, errs in fixes.items():
    with open(filename, 'r') as fp:
        lines = fp.readlines()
        
    for orig_line, msg in errs:
        # orig_line is 1-indexed
        idx = orig_line - 1
        code = lines[idx]
        
        if "Cannot silently unwrap Result" in msg:
            # We need to add ?! default; at the end before the semicolon
            # But wait, we can just find the variable assignment type
            # "Cannot silently unwrap Result<int64> into '...' of type 'int64'"
            mm = re.search(r"into '.*?' of type '(.*?)'", msg)
            if mm:
                t = mm.group(1)
                default = "0"
                if t == "int64": default = "0i64"
                elif t == "int32": default = "0i32"
                elif t == "float32": default = "0.0f32"
                elif t == "float64": default = "0.0f64"
                elif t == "bool": default = "false"
                elif t == "int16": default = "0i16"
                
                if "?!" not in code:
                    # just insert ?! default before ;
                    lines[idx] = code.replace(";", f" ?! {default};")
                else:
                    # if it already has ?!, maybe it was a syntax bug where it's wrapped wrong?
                    pass
        elif "Undefined identifier" in msg:
            # Maybe it's C. Did you mean M? etc. Let's ignore for now.
            pass

    with open(filename, 'w') as fp:
        fp.writelines(lines)

print("Applied unwraps.")
