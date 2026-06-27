with open('tests/test_query_ast/main.npk', 'r') as f:
    content = f.read()

content = content.replace('''    int64:arr_handles = npk_core_alloc(16i64);
    drop(npk_mem_write_int64(arr_handles, 0i64, o1));
    drop(npk_mem_write_int64(arr_handles, 8i64, o2));''',
                          '''    int64:o1_val = npk_core_alloc(16i64);
    drop(npk_mem_write_byte(o1_val, 0i64, JSON_OBJ));
    drop(npk_mem_write_int64(o1_val, 8i64, o1));
    
    int64:o2_val = npk_core_alloc(16i64);
    drop(npk_mem_write_byte(o2_val, 0i64, JSON_OBJ));
    drop(npk_mem_write_int64(o2_val, 8i64, o2));

    int64:arr_handles = npk_core_alloc(16i64);
    drop(npk_mem_write_int64(arr_handles, 0i64, o1_val));
    drop(npk_mem_write_int64(arr_handles, 8i64, o2_val));''')

with open('tests/test_query_ast/main.npk', 'w') as f:
    f.write(content)
