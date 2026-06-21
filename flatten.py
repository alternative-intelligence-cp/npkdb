import os, re

visited = set()
lines = []
line_map = {}
current_line = 1

def process_file(f):
    global current_line
    f = os.path.normpath(f)
    if f in visited:
        return
    visited.add(f)
    
    if not os.path.exists(f):
        print("Missing:", f)
        return
    
    base_dir = os.path.dirname(f)
    
    with open(f, 'r') as fp:
        for orig_line, line_content in enumerate(fp, 1):
            m = re.match(r'use\s+"([^"]+)"\.\*;', line_content)
            if m:
                target = m.group(1)
                # If absolute? Nitpick uses relative to current file.
                target_path = os.path.normpath(os.path.join(base_dir, target))
                if target == "unsafe.npk" and not os.path.exists(target_path):
                    target_path = "src/util/unsafe.npk"
                process_file(target_path)
                continue
            
            lines.append(line_content)
            line_map[current_line] = (f, orig_line)
            current_line += 1

process_file("tests/test_hnsw_graph/main.npk")

with open("build/flattened.npk", "w") as fp:
    fp.writelines(lines)

import json
with open("build/line_map.json", "w") as fp:
    json.dump(line_map, fp)

print("Flattened to build/flattened.npk")
