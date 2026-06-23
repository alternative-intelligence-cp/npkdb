import re

files = ['src/vector/hnsw_search.npk', 'src/vector/hnsw_insert.npk']
funcs = [
    'hnsw_pq_get_size', 'hnsw_pq_get_dist', 'hnsw_pq_get_slot', 'hnsw_pq_get_gen',
    'hnsw_graph_distance', 'hnsw_node_get_vector_offset', 'hnsw_node_get_num_neighbors',
    'hnsw_node_get_neighbor_slot', 'hnsw_node_get_neighbor_gen', 'hnsw_visited_check',
    'hnsw_graph_get_mL', 'rand_next', 'hnsw_pq_create', 'hnsw_arena_get_node',
    'hnsw_pq_get_elements', 'hnsw_select_neighbors', 'hnsw_pq_get_candidate_ptr',
    'hnsw_arena_alloc_node', 'hnsw_random_layer', 'hnsw_graph_get_max_layer',
    'hnsw_graph_get_M', 'hnsw_graph_get_M0', 'hnsw_graph_get_ef_construction',
    'hnsw_search_layer', 'hnsw_graph_get_arena'
]

for file in files:
    with open(file, 'r') as f:
        content = f.read()

    for func in funcs:
        content = re.sub(r'(?<!raw )(?<!func:)\b' + func + r'\(', r'raw ' + func + r'(', content)

    # Some variables like c_dist etc might have been completely borked by my manual edits.
    # We will let the compiler tell us.
    with open(file, 'w') as f:
        f.write(content)

print("done")
