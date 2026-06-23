import os
import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    orig_content = content
    
    # 1. @cast<Type>(expr) -> @cast_unchecked<Type>(expr)
    content = re.sub(r'@cast<([a-zA-Z0-9_\-]+(?:->)*)>\((.*?)\)', r'@cast_unchecked<\1>(\2)', content)

    # 2. expr => Type
    # Find all occurrences of =>
    pos = 0
    while True:
        idx = content.find("=>", pos)
        if idx == -1:
            break
            
        m = re.match(r'=>\s*([a-zA-Z0-9_]+(?:->)*)', content[idx:])
        if not m:
            pos = idx + 2
            continue
            
        t = m.group(1)
        end_idx = idx + len(m.group(0))
        
        i = idx - 1
        while i >= 0 and content[i].isspace():
            i -= 1
            
        if i < 0:
            pos = idx + 2
            continue
            
        if content[i] == ')':
            depth = 1
            i -= 1
            while i >= 0 and depth > 0:
                if content[i] == ')': depth += 1
                elif content[i] == '(': depth -= 1
                i -= 1
            
            # include function name or `@` or field access before parens
            while i >= 0 and (content[i].isalnum() or content[i] in ['_', '@', '.', '-', '>']):
                i -= 1
            start = i + 1
        else:
            start = i
            while start >= 0 and (content[start].isalnum() or content[start] in ['_', '@', '.', '-', '>']):
                start -= 1
            start += 1
            
        expr = content[start:idx].strip()
        before = content[:start]
        
        # SKIP if it involves fail
        if "fail(" in expr or "fail " in expr or expr == "fail":
            pos = idx + 2
            continue
            
        content = f"{before}@cast_unchecked<{t}>({expr}){content[end_idx:]}"
        pos = start + len(f"@cast_unchecked<{t}>({expr})")
        
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
