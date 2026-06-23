import re

files = ['src/vector/hnsw_search.npk', 'src/vector/hnsw_insert.npk']

for file in files:
    with open(file, 'r') as f:
        content = f.read()

    # 1. Replace '_?!' with 'raw '
    content = content.replace('_?!', 'raw ')

    # 2. Replace '? ...' with 'raw ' or remove the `? ...` completely based on whether the func returns a Result.
    # hnsw_pq_get_size returns int64 -> remove ` ? 0i64`
    content = re.sub(r'hnsw_pq_get_size\((.*?)\)\s*\?\s*0i64', r'hnsw_pq_get_size(\1)', content)
    
    # hnsw_pq_get_dist returns tfp64 -> remove ` ? 0.0tf` and ` ? 3.402823466e+38tf`
    content = re.sub(r'hnsw_pq_get_dist\((.*?)\)\s*\?\s*[0-9\.e\+]+tf', r'hnsw_pq_get_dist(\1)', content)

    # hnsw_pq_get_slot / hnsw_pq_get_gen return int32 -> remove ` ? 0i32`
    content = re.sub(r'hnsw_pq_get_slot\((.*?)\)\s*\?\s*0i32', r'hnsw_pq_get_slot(\1)', content)
    content = re.sub(r'hnsw_pq_get_gen\((.*?)\)\s*\?\s*0i32', r'hnsw_pq_get_gen(\1)', content)
    
    # hnsw_graph_distance returns tfp64 -> remove ` ? 3.402823466e+38tf` and ` ? 0.0tf`
    content = re.sub(r'hnsw_graph_distance\((.*?)\)\s*\?\s*[0-9\.e\+]+tf', r'hnsw_graph_distance(\1)', content)

    # hnsw_node_get_vector_offset returns int64 -> remove ` ? 0i64`
    content = re.sub(r'hnsw_node_get_vector_offset\((.*?)\)\s*\?\s*0i64', r'hnsw_node_get_vector_offset(\1)', content)
    
    # hnsw_node_get_num_neighbors returns int32 -> remove ` ? 0i32`
    content = re.sub(r'hnsw_node_get_num_neighbors\((.*?)\)\s*\?\s*0i32', r'hnsw_node_get_num_neighbors(\1)', content)
    
    # hnsw_node_get_neighbor_slot / _gen returns int32 -> remove ` ? 0i32`
    content = re.sub(r'hnsw_node_get_neighbor_slot\((.*?)\)\s*\?\s*0i32', r'hnsw_node_get_neighbor_slot(\1)', content)
    content = re.sub(r'hnsw_node_get_neighbor_gen\((.*?)\)\s*\?\s*0i32', r'hnsw_node_get_neighbor_gen(\1)', content)
    
    # hnsw_visited_check returns int64 -> remove ` ? 0i64`
    content = re.sub(r'hnsw_visited_check\((.*?)\)\s*\?\s*0i64', r'hnsw_visited_check(\1)', content)
    
    # Functions that return Result<int64> and need 'raw ':
    # hnsw_graph_get_arena, hnsw_arena_get_node, hnsw_pq_create
    for func in ['hnsw_graph_get_arena', 'hnsw_arena_get_node', 'hnsw_pq_create']:
        content = re.sub(r'(?<!raw )' + func + r'\((.*?)\)\s*\?\s*0i64', r'raw ' + func + r'(\1)', content)
        
    with open(file, 'w') as f:
        f.write(content)

print("done")
