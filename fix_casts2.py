import os
import re

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # We want to replace `<expr> => <type>` with `@cast_unchecked<<type>>(<expr>)`
    # A simple but safe way is to repeatedly apply the regex from inside out or find matching parentheses if needed.
    # Actually, we can use a token-based approach or just a cautious regex.
    # Pattern: `(\w+)\s*=>\s*(\w+)` -> `@cast_unchecked<\2>(\1)`
    # This handles `var => type` safely if it's alphanumeric.
    content = re.sub(r'\b([A-Za-z0-9_]+)\s*=>\s*([A-Za-z0-9_]+)\b', r'@cast_unchecked<\2>(\1)', content)

    # For parenthesized expressions like `(something => type)` that the above didn't catch?
    # We replaced `M => int64`, now what about `(expr) => type` where expr is in parens?
    # e.g., `(npk_mem_read_int64(rand_state_ptr, 0i64) => uint64)`
    # Let's find `=>` manually
    
    while '=>' in content:
        # find the right side (type)
        match = re.search(r'=>\s*([a-zA-Z0-9_]+)', content)
        if not match:
            break
        type_str = match.group(1)
        start_idx = match.start()
        end_idx = match.end()
        
        # trace back to find the left side expression
        i = start_idx - 1
        while i >= 0 and content[i].isspace():
            i -= 1
        
        if i < 0:
            break
            
        expr_end = i
        if content[i] == ')':
            # find matching parenthesis
            depth = 1
            i -= 1
            while i >= 0 and depth > 0:
                if content[i] == ')':
                    depth += 1
                elif content[i] == '(':
                    depth -= 1
                i -= 1
            expr_start = i + 1
            
            # include the function name before the parenthesis
            while i >= 0 and (content[i].isalnum() or content[i] == '_'):
                i -= 1
            expr_start = i + 1
        else:
            # find start of word
            while i >= 0 and (content[i].isalnum() or content[i] == '_'):
                i -= 1
            expr_start = i + 1
            
        expr = content[expr_start:expr_end+1]
        
        # replace
        replacement = f'@cast_unchecked<{type_str}>({expr})'
        content = content[:expr_start] + replacement + content[end_idx:]

    with open(filepath, 'w') as f:
        f.write(content)

for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith('.npk'):
            fix_file(os.path.join(root, file))

print("Fixed casts iteratively!")
