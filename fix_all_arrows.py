import os
import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    orig_content = content
    
    # 1. Replace @cast<Type>(expr) -> @cast_unchecked<Type>(expr)
    content = re.sub(r'@cast<([a-zA-Z0-9_\-]+(->)*)>\((.*?)\)', r'@cast_unchecked<\1>(\2)', content)

    # 2. Replace (expr) => Type and expr => Type
    # Since we can have `=> int64->` or `=> tbb32` etc., let's match `=>\s*([a-zA-Z0-9_]+(->)*)`
    while "=>" in content:
        idx = content.find("=>")
        m = re.match(r'=>\s*([a-zA-Z0-9_]+(?:->)*)', content[idx:])
        if not m:
            break
            
        t = m.group(1)
        end_idx = idx + len(m.group(0))
        
        lhs = content[:idx].rstrip()
        
        # We need to find the start of the expression on the left
        if lhs.endswith(")"):
            depth = 0
            start_idx = len(lhs) - 1
            for i in range(len(lhs)-1, -1, -1):
                if lhs[i] == ")": depth += 1
                elif lhs[i] == "(": 
                    depth -= 1
                    if depth == 0:
                        start_idx = i
                        break
            # check if there's a function call before the parens
            i = start_idx - 1
            while i >= 0 and (lhs[i].isalnum() or lhs[i] == '_'):
                i -= 1
            start_idx = i + 1
            
            expr = lhs[start_idx:]
            before = lhs[:start_idx]
            
            # If expr has outer parens, strip them for the cast, e.g. `(b_ptr)` -> `@cast_unchecked<tfp64->>(b_ptr)`
            # actually it's fine to keep them: `@cast_unchecked<tfp64->>((b_ptr))`
        else:
            # simple variable or number
            m2 = re.search(r'([a-zA-Z0-9_\.]+)$', lhs)
            if m2:
                expr = m2.group(1)
                before = lhs[:-len(expr)]
            else:
                # fallback
                expr = lhs[-1]
                before = lhs[:-1]
                
        # Now construct the replacement
        content = f"{before}@cast_unchecked<{t}>({expr}){content[end_idx:]}"
        
    if content != orig_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

if __name__ == "__main__":
    count = 0
    for root, dirs, files in os.walk('src'):
        for file in files:
            if file.endswith('.npk'):
                if process_file(os.path.join(root, file)):
                    count += 1
    print(f"Updated {count} files")
