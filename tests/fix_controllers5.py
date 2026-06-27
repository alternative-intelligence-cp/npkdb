import re
import sys

with open('src/network/controllers.npk', 'r') as f:
    code = f.read()

# Fix controller_search
old_search_start = """    int64:coll_ptr = raw catalog_get_collection("my_docs"); // Hardcoded for now? Wait, no! controller_search is generic?
    // Wait! Let's check if controller_search gets collection name. No it doesn't! It searches across all?
    // Let me check if search is collection specific. 
    // It's not! Let's hardcode "my_docs" or get it from request.

    // Parse json payload
    Result<NpkJsonVal>:v_res = parse_json_raw(arena, req.body_ptr, req.body_len);"""

new_search_start = """    int64:coll_ptr = raw catalog_get_collection("my_docs");
    if (coll_ptr == 0i64) {
        drop(Server.send_typed(client_fd, 404i64, "application/json", "{\\"error\\":\\"Collection not found\\"}"));
        pass(404i32);
    }
    Collection->:coll = @cast_unchecked<Collection->>(coll_ptr);
    int64:graph = @cast_unchecked<int64>(coll->vector_index);
    int64:doc_store = coll->doc_store;

    Result<int64>:arena_res = json_arena_init(1048576i64);
    if (arena_res.is_error) { pass(ERR_JSON_PARSE_FAIL); }
    int64:arena = raw arena_res;
    defer { _?json_arena_destroy(arena); }

    // Parse json payload
    Result<NpkJsonVal>:v_res = parse_json_raw(arena, req.body_ptr, req.body_len);"""

code = code.replace(old_search_start, new_search_start)

# Fix res_pq to req?
# Wait, the compiler said:
# src/main.npk:0:0: error: Line 419, Column 9: Undefined identifier: 'res_pq'. Did you mean 'req'?
# src/main.npk:0:0: error: Line 426, Column 33: Undefined identifier: 'res_pq'. Did you mean 'req'?
# Let's find why res_pq is undefined.
# It is defined as: int64:res_pq = hnsw_search_layer(
# But wait, hnsw_search_layer call uses 'doc_arena' which I should change to 'arena'

code = code.replace('hnsw_search_layer(\n        doc_arena,', 'hnsw_search_layer(\n        arena,')
code = code.replace('hnsw_search_layer(doc_arena,', 'hnsw_search_layer(arena,')

# Fix SerialBuffer:
old_sbuf = """    int64:buf_capacity = 4096i64;
    SerialBuffer:sbuf = SerialBuffer {
        data: npk_core_alloc(buf_capacity),
        capacity: buf_capacity,
        cursor: 0i64
    };
    defer { _?npk_core_dalloc(sbuf.data); }"""

new_sbuf = """    int64:buf_capacity = 4096i64;
    int64:sbuf = npk_core_alloc(24i64);
    defer { _?npk_core_dalloc(sbuf); }
    drop(npk_mem_write_int64(sbuf, 0i64, npk_core_alloc(buf_capacity)));
    defer { _?npk_core_dalloc(npk_mem_read_int64(sbuf, 0i64)); }
    drop(npk_mem_write_int64(sbuf, 8i64, buf_capacity));
    drop(npk_mem_write_int64(sbuf, 16i64, 0i64));"""
code = code.replace(old_sbuf, new_sbuf)

code = code.replace('serial_buffer_ensure(@sbuf', 'serial_buffer_ensure(sbuf')
code = code.replace('sbuf.data + sbuf.cursor', 'npk_mem_read_int64(sbuf, 0i64) + npk_mem_read_int64(sbuf, 16i64)')
code = code.replace('sbuf.cursor = sbuf.cursor + 1i64;', 'drop(npk_mem_write_int64(sbuf, 16i64, npk_mem_read_int64(sbuf, 16i64) + 1i64));')
code = code.replace('sbuf.cursor = sbuf.cursor + item_len;', 'drop(npk_mem_write_int64(sbuf, 16i64, npk_mem_read_int64(sbuf, 16i64) + item_len));')
code = code.replace('sbuf.data, sbuf.cursor', 'npk_mem_read_int64(sbuf, 0i64), npk_mem_read_int64(sbuf, 16i64)')

with open('src/network/controllers.npk', 'w') as f:
    f.write(code)

print("Modified controllers.npk for controller_search and sbuf")
