with open('src/query/path_eval.npk', 'r') as f:
    content = f.read()

content = content.replace('    int64:seg_len = raw path_segment_len(path_ptr);',
                          '''    int64:seg_len = raw path_segment_len(path_ptr);
    println("EVAL_PATH seg_len:");
    println(string_from_int(seg_len));''')

content = content.replace('        if (k_type == JSON_STR) {',
                          '''        if (k_type == JSON_STR) {
            println("Found JSON_STR key");
            int64:k_len_dbg = cast_unchecked<int64>(npk_mem_read_int32(k_payload, 0i64));
            println("k_len:");
            println(string_from_int(k_len_dbg));''')

with open('src/query/path_eval.npk', 'w') as f:
    f.write(content)
