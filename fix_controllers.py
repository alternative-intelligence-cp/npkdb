with open('src/network/controllers.npk', 'r') as f: content = f.read()
old = """    int64:ep_node_ptr = hnsw_graph_get_entry_point(global_graph) ? 0i64;
    int32:ep_slot = -1i32;
    int32:ep_gen = 0i32;

    if (ep_node_ptr != 0i64) {
        ep_slot = hnsw_node_get_slot(ep_node_ptr) ? -1i32;
        ep_gen = hnsw_node_get_generation(ep_node_ptr) ? 0i32;
    }"""
new = """    int64:ep_slot_ptr = npk_core_alloc(4i64);
    int64:ep_gen_ptr = npk_core_alloc(4i64);
    defer { _?npk_core_dalloc(ep_slot_ptr); _?npk_core_dalloc(ep_gen_ptr); }
    int64:ep_node_ptr = hnsw_graph_get_ep(global_graph, ep_slot_ptr, ep_gen_ptr);
    int32:ep_slot = -1i32;
    int32:ep_gen = 0i32;
    if (ep_node_ptr != 0i64) {
        ep_slot = npk_mem_read_int32(ep_slot_ptr, 0i64) => int32;
        ep_gen = npk_mem_read_int32(ep_gen_ptr, 0i64) => int32;
    }"""
if old in content:
    with open('src/network/controllers.npk', 'w') as f: f.write(content.replace(old, new))
else:
    print("Not found in controllers.npk")
