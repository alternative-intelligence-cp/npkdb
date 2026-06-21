import re
filepath = 'tests/test_distance_props/main.npk'
with open(filepath, 'r') as f:
    content = f.read()

def repl_write(m):
    ptr = m.group(1)
    offset = m.group(2)
    val = m.group(3)
    if offset == '0i64':
        idx = '0i64'
    elif offset.endswith(' * 8i64'):
        idx = offset[:-7]
    else:
        idx = f'({offset}) / 8i64'
    return f'(@cast_unchecked<tfp64->>({ptr}))[{idx}] = {val}'

content = re.sub(r'drop\(npk_mem_write_tfp64\(([^,]+),\s*([^,]+),\s*([^)]+)\)\)', repl_write, content)
content = re.sub(r'npk_mem_write_tfp64\(([^,]+),\s*([^,]+),\s*([^)]+)\)', repl_write, content)

def repl_read(m):
    ptr = m.group(1)
    offset = m.group(2)
    if offset == '0i64':
        idx = '0i64'
    elif offset.endswith(' * 8i64'):
        idx = offset[:-7]
    else:
        idx = f'({offset}) / 8i64'
    return f'(@cast_unchecked<tfp64->>({ptr}))[{idx}]'

content = re.sub(r'npk_mem_read_tfp64\(([^,]+),\s*([^)]+)\)', repl_read, content)

with open(filepath, 'w') as f:
    f.write(content)
