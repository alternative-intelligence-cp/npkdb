import re

with open("tests/test_single_stage_filter/main.npk", "r") as f:
    content = f.read()

# Replace the doc construction inside the while (i < 10i64) loop
doc_creation = """        int64:doc_arena = raw json_arena_init(1024i64);
        
        // v_str: "A" or "B" (len=1)
        int64:v_str_payload = raw json_arena_alloc(doc_arena, 16i64);
        drop(npk_mem_write_int32(v_str_payload, 0i64, 1i32));
        drop(npk_mem_write_int64(v_str_payload, 8i64, val_str));
        NpkJsonVal:v_str = NpkJsonVal { type: 3i8, payload: v_str_payload };

        // v_key: k_cat.data (len=8)
        int64:v_key_payload = raw json_arena_alloc(doc_arena, 16i64);
        drop(npk_mem_write_int32(v_key_payload, 0i64, 8i32));
        drop(npk_mem_write_int64(v_key_payload, 8i64, k_cat.data));
        NpkJsonVal:v_key = NpkJsonVal { type: 3i8, payload: v_key_payload };
        
        int64:keys_ptr = raw json_arena_alloc(doc_arena, 16i64);
        drop(npk_mem_write_byte(keys_ptr, 0i64, @cast_unchecked<int8>(v_key.type)));
        drop(npk_mem_write_int64(keys_ptr, 8i64, v_key.payload));
        
        int64:vals_ptr = raw json_arena_alloc(doc_arena, 16i64);
        drop(npk_mem_write_byte(vals_ptr, 0i64, @cast_unchecked<int8>(v_str.type)));
        drop(npk_mem_write_int64(vals_ptr, 8i64, v_str.payload));
        
        int64:k_arr = raw json_arena_alloc(doc_arena, 8i64);
        drop(npk_mem_write_int64(k_arr, 0i64, keys_ptr));
        int64:v_arr = raw json_arena_alloc(doc_arena, 8i64);
        drop(npk_mem_write_int64(v_arr, 0i64, vals_ptr));

        int64:obj_ptr = raw json_arena_alloc(doc_arena, 24i64);
        drop(npk_mem_write_int32(obj_ptr, 0i64, 1i32));
        drop(npk_mem_write_int64(obj_ptr, 8i64, k_arr));
        drop(npk_mem_write_int64(obj_ptr, 16i64, v_arr));
        
        NpkJsonVal:doc = NpkJsonVal { type: 4i8, payload: obj_ptr };
        
        int64:len_ptr = npk_core_alloc(8i64);
        int64:doc_buf = raw serialize_document(doc, len_ptr);
        drop(npk_mem_write_int64(doc_store, i * 8i64, doc_buf));
"""

old_doc_creation = r"""        int64:doc_arena = raw json_arena_init\(1024i64\);.*?drop\(npk_mem_write_int64\(doc_store, i \* 8i64, doc_buf\)\);"""
content = re.sub(old_doc_creation, doc_creation, content, flags=re.DOTALL)

with open("tests/test_single_stage_filter/main.npk", "w") as f:
    f.write(content)
