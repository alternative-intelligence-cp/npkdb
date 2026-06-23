import os
import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    orig_content = content
    
    # We want to replace `@cast_unchecked<Type>(expr)` with `(expr) => Type`
    # We need to be careful with nested parens, but regex might work if `expr` is simple
    # Or just use a simple regex for the ones we converted
    
    # We converted: `@cast_unchecked<t>(expr)`
    # Let's find `@cast_unchecked<`
    while "@cast_unchecked<" in content:
        idx = content.find("@cast_unchecked<")
        # find closing >
        type_start = idx + 16
        type_end = content.find(">", type_start)
        
        # wait, if type is NpkJsonVal->>, then the first > is part of ->
        if content[type_end-1] == '-' and content[type_end] == '>':
            type_end += 1 # move past the ->
            # then the next char should be >
            if content[type_end] == '>':
                type_end += 1
            else:
                pass # something is wrong
                
        type_str = content[type_start:type_end]
        if type_str.endswith('>'):
            type_str = type_str[:-1]
            type_end -= 1
            
        # check for the exact closing >
        if content[type_end] == '>':
            pass
            
        expr_start = type_end + 1
        if content[expr_start] != '(':
            break
            
        # find matching paren
        depth = 1
        expr_end = expr_start + 1
        while expr_end < len(content) and depth > 0:
            if content[expr_end] == '(': depth += 1
            elif content[expr_end] == ')': depth -= 1
            expr_end += 1
            
        expr = content[expr_start+1:expr_end-1]
        
        before = content[:idx]
        after = content[expr_end:]
        
        content = f"{before}({expr}) => {type_str}{after}"
        
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
    print(f"Reverted {count} files")
