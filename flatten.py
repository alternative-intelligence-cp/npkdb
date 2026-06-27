import os, re

visited = set()
lines = []
line_map = {}
current_line = 1

def process_file(f):
    global current_line
    f = os.path.abspath(f)
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
                target_path = os.path.abspath(os.path.join(base_dir, target))
                    
                if not os.path.exists(target_path):
                    # Leave stdlib imports intact for nitpickc to resolve
                    lines.append(line_content)
                    line_map[current_line] = (f, orig_line)
                    current_line += 1
                    continue
                    
                process_file(target_path)
                continue
            
            lines.append(line_content)
            line_map[current_line] = (f, orig_line)
            current_line += 1

import sys
import json

entry_point = sys.argv[1] if len(sys.argv) > 1 else "src/main.npk"
process_file(entry_point)

with open("build/flattened.npk", "w") as fp:
    fp.write('use "unsafe.npk".*;\n')
    fp.writelines(lines)

with open("build/line_map.json", "w") as fp:
    json.dump(line_map, fp)

print("Flattened to build/flattened.npk")
