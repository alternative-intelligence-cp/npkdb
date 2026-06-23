import os
import re

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Replace ((expr) => Type) -> @cast_unchecked<Type>(expr)
    # Wait, the syntax might be `expr => Type` or `(expr) => Type`.
    # It's safer to look at specific lines.
    # But wait! I can just replace `=> Type` with `@cast_unchecked<Type>` using regex!
    # Pattern: `(expr) => Type` where expr is anything inside matched parens.
    # Or just `expr => Type` if expr is a simple variable name.
    
    # Actually, replacing all `=> Type` might be hard if we don't know the LHS.
    # Let's replace `@cast<Type>(expr)` -> `@cast_unchecked<Type>(expr)`
    content = re.sub(r'@cast<([a-zA-Z0-9_]+)>\((.*?)\)', r'@cast_unchecked<\1>(\2)', content)
    
    # For `expr => Type`, we can do a simple regex if it's mostly `(expr) => Type` or `var => Type`
    # Let's match `([a-zA-Z0-9_\.\(\)]+) => ([a-zA-Z0-9_]+)` and turn it into `@cast_unchecked<\2>(\1)`
    # This might be tricky because of nested parens.
    # A safer way is to find `=>` and replace it manually or with a simple script that parses backwards.
    
    # Since I already have a mapped_warnings.txt, maybe I can just find the exact lines!
    # Let's read mapped_warnings.txt and fix the specific lines.
    pass

if __name__ == "__main__":
    with open("mapped_warnings.txt", "r") as f:
        lines = f.readlines()
        
    file_mods = {}
    for line in lines:
        if " - warning: " in line:
            parts = line.split(" - warning: ")
            loc = parts[0]
            if ":" in loc:
                fname, lno = loc.split(":")
                lno = int(lno)
                msg = parts[1]
                
                if fname not in file_mods:
                    try:
                        with open(fname, "r") as src:
                            file_mods[fname] = src.read().split("\n")
                    except Exception:
                        pass
                
                if fname in file_mods:
                    # Look at the line
                    if lno > 0 and lno <= len(file_mods[fname]):
                        code_line = file_mods[fname][lno-1]
                        
                        # Replace @cast<Type>
                        code_line = re.sub(r'@cast<([a-zA-Z0-9_]+)>', r'@cast_unchecked<\1>', code_line)
                        
                        # Replace `=> Type`
                        # We can do a simple search for `=>`
                        while "=>" in code_line:
                            idx = code_line.find("=>")
                            # Find RHS type
                            m = re.match(r'=>\s*([a-zA-Z0-9_]+)', code_line[idx:])
                            if m:
                                t = m.group(1)
                                end_idx = idx + len(m.group(0))
                                
                                # Find LHS expr
                                lhs = code_line[:idx].strip()
                                # Simple parse backwards: if ends with ), find matching (. Else find last word.
                                if lhs.endswith(")"):
                                    # find matching paren
                                    depth = 0
                                    start_idx = len(lhs) - 1
                                    for i in range(len(lhs)-1, -1, -1):
                                        if lhs[i] == ")": depth += 1
                                        elif lhs[i] == "(": 
                                            depth -= 1
                                            if depth == 0:
                                                start_idx = i
                                                break
                                    # Sometimes there is stuff before (, like function call.
                                    # Let's just wrap the whole thing we found
                                    expr = lhs[start_idx:]
                                    before = lhs[:start_idx]
                                else:
                                    # just take the last word
                                    words = re.split(r'([^a-zA-Z0-9_\.])', lhs)
                                    expr = words[-1]
                                    before = "".join(words[:-1])
                                
                                code_line = f"{before}@cast_unchecked<{t}>({expr}){code_line[end_idx:]}"
                            else:
                                break
                                
                        file_mods[fname][lno-1] = code_line
                        
    for fname, content_lines in file_mods.items():
        with open(fname, "w") as f:
            f.write("\n".join(content_lines))

    print(f"Fixed {len(file_mods)} files")
