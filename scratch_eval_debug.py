import re

with open("src/query/evaluator.npk", "r") as f:
    content = f.read()

debug_prints = """            if (actual.type == JSON_STR) {
                int64:a_len = @cast_unchecked<int64>(npk_mem_read_int32(actual.payload, 0i64));
                int64:t_len = @cast_unchecked<int64>(npk_mem_read_int32(target.payload, 0i64));
                
                println("comparing strings!");
                println(a_len);
                println(t_len);
"""

content = content.replace("""            if (actual.type == JSON_STR) {
                int64:a_len = @cast_unchecked<int64>(npk_mem_read_int32(actual.payload, 0i64));
                int64:t_len = @cast_unchecked<int64>(npk_mem_read_int32(target.payload, 0i64));""", debug_prints)

with open("src/query/evaluator.npk", "w") as f:
    f.write(content)
