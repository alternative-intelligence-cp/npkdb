import os
import re

def fix_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Broken calls like: (npk_mem_read_int64(graph, HNSW_GRAPH_OFF_ML => float64)) -> (npk_mem_read_int64(graph, HNSW_GRAPH_OFF_ML) => float64)
    content = re.sub(r'\(npk_mem_read_int64\([^)]+,\s*[^)=]+(\s*=>\s*float64)\)', 
                     lambda m: m.group(0).replace(' => float64)', ') => float64'), content)
                     
    content = re.sub(r'\(npk_mem_read_int32\([^)]+,\s*[^)=]+(\s*=>\s*float32)\)', 
                     lambda m: m.group(0).replace(' => float32)', ') => float32'), content)

    content = re.sub(r'\(npk_mem_read_int64\([^)]+,\s*[^)=]+(\s*=>\s*uint64)\)', 
                     lambda m: m.group(0).replace(' => uint64)', ') => uint64'), content)

    content = re.sub(r'\(npk_mem_read_int64\([^)]+,\s*[^)=]+(\s*=>\s*int32)\)', 
                     lambda m: m.group(0).replace(' => int32)', ') => int32'), content)

    # Broken calls like (floor(l_val => int32)) -> (floor(l_val) => int32)
    content = re.sub(r'\(floor\([^)]+(\s*=>\s*int32)\)', 
                     lambda m: m.group(0).replace(' => int32)', ') => int32'), content)

    # Double parens around simple casts: ((M => int64)) -> (M => int64)
    content = re.sub(r'\(\(([a-zA-Z0-9_]+)\s*=>\s*([a-zA-Z0-9_]+)\)\)', r'(\1 => \2)', content)

    # Some fail calls: fail((ERR_HNSW_OOM => tbb8)) -> fail(ERR_HNSW_OOM => tbb8)
    content = re.sub(r'fail\(\(([A-Za-z0-9_]+)\s*=>\s*tbb8\)\)', r'fail(\1 => tbb8)', content)

    # (val => type) -> val => type for simple arguments? 
    # Let's leave them if they compile. Nitpick accepts extra parens around `expr => type`.

    with open(filepath, 'w') as f:
        f.write(content)

for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith('.npk'):
            fix_file(os.path.join(root, file))

for root, dirs, files in os.walk('tests'):
    for file in files:
        if file.endswith('.npk'):
            fix_file(os.path.join(root, file))

print("Fixed parens!")
