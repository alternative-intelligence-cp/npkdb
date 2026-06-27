import re
import sys

with open('src/network/controllers.npk', 'r') as f:
    code = f.read()

# 1. Replace all 'free(' with 'npk_core_dalloc('
code = code.replace('free(', 'npk_core_dalloc(')

# 2. Replace 'serialize_document(@elem, len_out)' with 'serialize_document(elem, len_out)'
code = code.replace('serialize_document(@elem, len_out)', 'serialize_document(elem, len_out)')

# 3. Lift temp_vec definition
code = code.replace('int64:temp_vec = npk_core_alloc(1024i64);', 'temp_vec = npk_core_alloc(1024i64);')
code = code.replace('defer { _?npk_core_dalloc(temp_vec); }', '')
# Insert int64:temp_vec = 0i64; right before int64:v_idx = 0i64;
code = code.replace('int64:v_idx = 0i64;', 'int64:temp_vec = 0i64;\n                                        int64:v_idx = 0i64;')

# Add npk_core_dalloc(temp_vec) after its usage
target = 'drop(npk_mem_write_int64(doc_store, hnsw_slot * 8i64, persistent_doc));'
code = code.replace(target, target + '\n                                            if (temp_vec != 0i64) { drop(npk_core_dalloc(temp_vec)); }')

with open('src/network/controllers.npk', 'w') as f:
    f.write(code)

print("Modified controllers.npk")
