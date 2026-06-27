import re

with open("src/query/path_eval.npk", "r") as f:
    content = f.read()

debug_prints = """        int8:k_type = @cast_unchecked<int8>(npk_mem_read_byte(k_ptr, 0i64));
        int64:k_payload = npk_mem_read_int64(k_ptr, 8i64);
        
        println("k_type:");
        println(@cast_unchecked<int64>(k_type));
        
        if (k_type == JSON_STR) {"""

content = content.replace("""        int8:k_type = @cast_unchecked<int8>(npk_mem_read_byte(k_ptr, 0i64));
        int64:k_payload = npk_mem_read_int64(k_ptr, 8i64);
        
        if (k_type == JSON_STR) {""", debug_prints)

with open("src/query/path_eval.npk", "w") as f:
    f.write(content)
