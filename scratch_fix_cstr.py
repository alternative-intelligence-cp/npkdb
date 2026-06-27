import os
import re

src_dir = "/home/randy/Workspace/REPOS/npkdb/src"

for root, _, files in os.walk(src_dir):
    for file in files:
        if file.endswith(".npk"):
            path = os.path.join(root, file)
            with open(path, "r") as f:
                lines = f.readlines()
            
            # Find all variables assigned from string_to_cstr
            cstr_vars = set()
            for line in lines:
                m = re.search(r'([a-zA-Z0-9_]+)\s*=\s*string_to_cstr\(', line)
                if m:
                    cstr_vars.add(m.group(1))
            
            if not cstr_vars:
                continue

            # Remove drop(npk_core_dalloc(var)) or drop(free(var)) for these vars
            new_lines = []
            changed = False
            for line in lines:
                remove = False
                for v in cstr_vars:
                    # check if line contains drop(npk_core_dalloc(v)) or raw npk_core_dalloc(v)
                    # or drop(free(v)) or raw free(v)
                    pat = rf'(drop|raw)\s*\(\s*(npk_core_dalloc|free)\s*\(\s*{v}\s*\)\s*\)'
                    pat2 = rf'(drop|raw)\s+(npk_core_dalloc|free)\s*\(\s*{v}\s*\)'
                    if re.search(pat, line) or re.search(pat2, line) or re.search(rf'drop\(npk_core_dalloc\({v}\)\)', line):
                        remove = True
                        break
                if not remove:
                    new_lines.append(line)
                else:
                    changed = True
            
            if changed:
                with open(path, "w") as f:
                    f.writelines(new_lines)
                print(f"Fixed {path}")
