import re

with open('src/vector/hnsw_insert.npk', 'r') as f:
    content = f.read()

content = content.replace('raw hnsw_pq_get_slot', 'hnsw_pq_get_slot')
content = content.replace('raw hnsw_pq_get_gen', 'hnsw_pq_get_gen')
content = content.replace('raw hnsw_pq_get_dist', 'hnsw_pq_get_dist')

with open('src/vector/hnsw_insert.npk', 'w') as f:
    f.write(content)

with open('src/network/controllers.npk', 'r') as f:
    content = f.read()

# Fix sz
content = re.sub(r'Result<int64>:sz_res = hnsw_pq_get_size\(res_pq\);\s*int64:sz = _!sz_res;', r'int64:sz = raw hnsw_pq_get_size(res_pq);', content)
# Fix dist
content = re.sub(r'Result<tfp64>:dist_res = hnsw_pq_get_dist\(C\);\s*tfp64:dist = raw dist_res;', r'tfp64:dist = hnsw_pq_get_dist(C);', content)
# Fix slot
content = re.sub(r'Result<int32>:slot_res = hnsw_pq_get_slot\(C\);\s*int32:slot = raw slot_res;', r'int32:slot = hnsw_pq_get_slot(C);', content)

with open('src/network/controllers.npk', 'w') as f:
    f.write(content)

print("fixed again")
