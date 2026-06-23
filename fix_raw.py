import re

files = ['src/vector/hnsw_search.npk', 'src/vector/hnsw_insert.npk']
funcs = [
    'hnsw_pq_get_size', 'hnsw_pq_get_dist', 'hnsw_pq_get_slot', 'hnsw_pq_get_gen',
    'hnsw_graph_distance', 'hnsw_node_get_vector_offset', 'hnsw_node_get_num_neighbors',
    'hnsw_node_get_neighbor_slot', 'hnsw_node_get_neighbor_gen', 'hnsw_visited_check'
]

for file in files:
    with open(file, 'r') as f:
        content = f.read()

    for func in funcs:
        content = re.sub(r'(?<!raw )' + func + r'\(', r'raw ' + func + r'(', content)

    with open(file, 'w') as f:
        f.write(content)

print("done")
