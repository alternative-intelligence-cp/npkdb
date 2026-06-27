import re

with open("src/query/path_eval.npk", "r") as f:
    content = f.read()

debug_prints = """        if (k_type == JSON_STR) {
            int64:k_len = @cast_unchecked<int64>(npk_mem_read_int32(k_payload, 0i64));
            println("k_len vs seg_len:");
            println(k_len);
            println(seg_len);
            if (k_len == seg_len) {"""

content = content.replace("""        if (k_type == JSON_STR) {
            int64:k_len = @cast_unchecked<int64>(npk_mem_read_int32(k_payload, 0i64));
            if (k_len == seg_len) {""", debug_prints)

with open("src/query/path_eval.npk", "w") as f:
    f.write(content)
