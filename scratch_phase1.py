import os
import re

def fix_unwraps(content):
    # Functions to unwrap
    funcs = ["npk_core_alloc", "json_arena_alloc", "page_alloc", "sys"]
    
    for func in funcs:
        # We want to find occurrences of func( that are not preceded by 'raw ', '_?', '?', or 'func:'
        # e.g., 'int64:buf = npk_core_alloc(' -> 'int64:buf = raw npk_core_alloc('
        
        # We will iterate and replace:
        # Regex to find func(
        pattern = r'([a-zA-Z0-9_=:\s]+?)\s*\b' + func + r'\s*\('
        
        def repl(match):
            prefix = match.group(1)
            # If prefix already ends with 'raw' or '?' or 'func:' or 'def ', we skip
            if prefix.endswith('raw') or prefix.endswith('?') or prefix.endswith('func:') or prefix.endswith('def'):
                return match.group(0)
            if prefix.strip() == '':
                return match.group(0) # Not sure
            # If it's an assignment or return, 'raw ' is usually fine
            if '=' in prefix or 'pass' in prefix or 'return' in prefix or 'int64:' in prefix or 'int32:' in prefix or prefix.endswith('('):
                return prefix + ' raw ' + func + '('
            return match.group(0)
            
        content = re.sub(pattern, repl, content)
        
        # Also fix drop(func(...)) to _?func(...)
        content = re.sub(r'drop\(\s*' + func + r'\s*\(', r'_?' + func + '(', content)
        
    return content

# Also apply to tests
dirs_to_search = ["src", "tests"]
for d in dirs_to_search:
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith(".npk"):
                path = os.path.join(root, f)
                with open(path, "r") as src:
                    content = src.read()
                
                new_content = fix_unwraps(content)
                if new_content != content:
                    with open(path, "w") as out:
                        out.write(new_content)
                    print(f"Fixed unwraps in {path}")
