import re

with open("src/query/path_eval.npk", "r") as f:
    content = f.read()

debug_prints = """pub func:eval_path = NpkJsonVal(int64:path_ptr, int64:doc_raw_ptr) {
    if (doc_raw_ptr == 0i64) {
        println("eval_path: doc_raw_ptr is 0");
        pass(raw json_make_null());
    }

    if (path_ptr == 0i64) {
        println("eval_path: path_ptr is 0");
        pass(raw json_make_null());
    }
    
    int64:seg_len = raw path_segment_len(path_ptr);
    if (seg_len == 0i64) {
        println("eval_path: seg_len is 0");
        pass(raw json_make_null());
    }
    
    int8:doc_type = @cast_unchecked<int8>(npk_mem_read_byte(doc_raw_ptr, 0i64));
    if (doc_type != JSON_OBJ) {
        println("eval_path: doc_type is NOT OBJ");
        println(@cast_unchecked<int64>(doc_type));
        pass(raw json_make_null());
    }
    
    int64:obj_ptr = npk_mem_read_int64(doc_raw_ptr, 8i64);"""

content = re.sub(r"""pub func:eval_path = NpkJsonVal\(int64:path_ptr, int64:doc_raw_ptr\) \{.*?int64:obj_ptr = npk_mem_read_int64\(doc_raw_ptr, 8i64\);""", debug_prints, content, flags=re.DOTALL)

with open("src/query/path_eval.npk", "w") as f:
    f.write(content)
