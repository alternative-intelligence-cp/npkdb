import os, re

def fix_file(fpath):
    with open(fpath, 'r') as f:
        content = f.read()
    
    # If a line has 'raw ' and '?!', remove the '?! <default>' part up to the semicolon
    lines = content.split('\n')
    changed = False
    for i, line in enumerate(lines):
        if 'raw ' in line and '?!' in line:
            # remove ?! and anything after it up to ;
            new_line = re.sub(r'\?!.*?;', ';', line)
            if new_line != line:
                lines[i] = new_line
                changed = True
        elif 'raw ' in line and '?' in line and '?!' not in line:
            # sometimes it's ? instead of ?!
            new_line = re.sub(r'\?.*?;', ';', line)
            if new_line != line:
                lines[i] = new_line
                changed = True
                
    if changed:
        with open(fpath, 'w') as f:
            f.write('\n'.join(lines))
        print(f"Fixed {fpath}")

for root, dirs, files in os.walk('src'):
    for f in files:
        if f.endswith('.npk'):
            fix_file(os.path.join(root, f))
