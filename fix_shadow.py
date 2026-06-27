import os, glob

for filepath in glob.glob("**/*.npk", recursive=True):
    if "mem_primitives.npk" in filepath: continue
    content = open(filepath).read()
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        if "func:nitpick_libc_rwlock_" in line and "=" in line and ("int64" in line or "int32" in line):
            continue
        new_lines.append(line)
    open(filepath, 'w').write('\n'.join(new_lines))
print("Done shadow fix")
