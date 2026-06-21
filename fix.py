import re
filepath = 'tests/test_distance_props/main.npk'
with open(filepath, 'r') as f:
    lines = f.readlines()

def fix_line(line):
    # Fix the corrupted lines manually based on their contents
    if 'i * 8i64 + (@cast_unchecked<tfp64->>(b))[(i]) / 8i64]' in line:
        return line.replace('i * 8i64 + (@cast_unchecked<tfp64->>(b))[(i]) / 8i64]', '(@cast_unchecked<tfp64->>(a))[i] + (@cast_unchecked<tfp64->>(b))[i]')
    if 'drop(npk_mem_write_tfp64' in line:
        # replace `drop(npk_mem_write_tfp64(ptr, offset, val))` with pointer indexing
        pass
    return line

with open(filepath, 'w') as f:
    for line in lines:
        f.write(fix_line(line))
