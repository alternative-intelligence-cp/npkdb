import os
import re
import sys

numeric_types = {
    'int8', 'int16', 'int32', 'int64',
    'uint8', 'uint16', 'uint32', 'uint64',
    'tbb8', 'tbb16', 'tbb32', 'tbb64',
    'flt32', 'flt64', 'tfp64', 'float64',
    'tryte', 'nyte', 'trit'
}

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    orig_content = content
    
    pos = 0
    while True:
        idx = content.find("=>", pos)
        if idx == -1:
            break
            
        m = re.match(r'=>\s*([a-zA-Z0-9_]+(?:->)*)', content[idx:])
        if not m:
            pos = idx + 2
            continue
            
        t = m.group(1).strip()
        end_idx = idx + len(m.group(0))
        
        if t not in numeric_types:
            pos = idx + 2
            continue
            
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
        
        # SKIP fail() again because it causes syntax errors
        if "fail(" in expr or "fail " in expr or expr == "fail" or "return" in expr:
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
    target_dir = sys.argv[1] if len(sys.argv) > 1 else 'src'
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith('.npk'):
                if process_file(os.path.join(root, file)):
                    count += 1
    print(f"Updated {count} files in {target_dir}")
