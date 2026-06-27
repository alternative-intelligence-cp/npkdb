with open('tests/test_query_ast/main.npk', 'r') as f:
    content = f.read()

import re

# Fix @cast_unchecked syntax
content = re.sub(r'drop\(npk_mem_write_byte@cast_unchecked<int64>\((.*?), 0i64, (.*?) \)\);', r'drop(npk_mem_write_byte(\1, 0i64, cast_unchecked<int64>(\2)));', content)
content = re.sub(r'drop\(npk_mem_write_int32\(obj, 0i64, @cast_unchecked<int32>\(len\)\)\);', r'drop(npk_mem_write_int32(obj, 0i64, cast_unchecked<int32>(len)));', content)
content = re.sub(r'int64:op = npk_mem_read_byte@cast_unchecked<int64>\(node_ptr, 0i64\);', r'int64:op = cast_unchecked<int64>(npk_mem_read_byte(node_ptr, 0i64));', content)
content = re.sub(r'int64:count = npk_mem_read_int32@cast_unchecked<int64>\(node_ptr, 32i64\);', r'int64:count = cast_unchecked<int64>(npk_mem_read_int32(node_ptr, 32i64));', content)
content = re.sub(r'type: npk_mem_read_byte@cast_unchecked<int8>\(node_ptr, 16i64\),', r'type: cast_unchecked<int8>(npk_mem_read_byte(node_ptr, 16i64)),', content)
content = re.sub(r'int64:a_len = npk_mem_read_int32@cast_unchecked<int64>\(actual.payload, 0i64\);', r'int64:a_len = cast_unchecked<int64>(npk_mem_read_int32(actual.payload, 0i64));', content)
content = re.sub(r'int64:t_len = npk_mem_read_int32@cast_unchecked<int64>\(target.payload, 0i64\);', r'int64:t_len = cast_unchecked<int64>(npk_mem_read_int32(target.payload, 0i64));', content)

# Fix parse_filter and eval_ast arguments
content = re.sub(r'int64:ast_root = raw parse_filter\(arena, @cast_unchecked<int64>\(@query\)\);', r'int64:ast_root = raw parse_filter(arena, query.payload, 0i32);', content)
content = re.sub(r'int8:root_op = npk_mem_read_byte@cast_unchecked<int8>\(ast_root, 0i64\);', r'int8:root_op = cast_unchecked<int8>(npk_mem_read_byte(ast_root, 0i64));', content)
content = re.sub(r'bool:match = raw eval_ast\(ast_root, @cast_unchecked<int64>\(@doc\)\);', r'bool:match = raw eval_ast(ast_root, doc.payload);', content)

# Fix make_json_str
content = re.sub(
    r'    int64:data = npk_core_alloc\(len \+ 1i64\);\n    drop\(npk_mem_write_string\(data, s\)\);',
    r'    int64:data = string_to_cstr(s);',
    content
)

# Fix arr_handles
arr_handles_old = r'''    int64:arr_handles = npk_core_alloc(16i64);
    int64:y_ptr = npk_core_alloc(16i64);
    drop(npk_mem_write_byte@cast_unchecked<int64>(y_ptr, 0i64, JSON_OBJ ));
    drop(npk_mem_write_int64(y_ptr, 8i64, y_obj));
    int64:g_ptr = npk_core_alloc(16i64);
    drop(npk_mem_write_byte@cast_unchecked<int64>(g_ptr, 0i64, JSON_OBJ ));
    drop(npk_mem_write_int64(g_ptr, 8i64, g_obj));
    drop(npk_mem_write_int64(arr_handles, 0i64, y_ptr));
    drop(npk_mem_write_int64(arr_handles, 8i64, g_ptr));'''

arr_handles_new = r'''    int64:arr_handles = npk_core_alloc(16i64);
    int64:y_ptr = npk_core_alloc(16i64);
    drop(npk_mem_write_byte(y_ptr, 0i64, cast_unchecked<int64>(JSON_OBJ)));
    drop(npk_mem_write_int64(y_ptr, 8i64, y_obj));
    int64:g_ptr = npk_core_alloc(16i64);
    drop(npk_mem_write_byte(g_ptr, 0i64, cast_unchecked<int64>(JSON_OBJ)));
    drop(npk_mem_write_int64(g_ptr, 8i64, g_obj));
    drop(npk_mem_write_int64(arr_handles, 0i64, y_ptr));
    drop(npk_mem_write_int64(arr_handles, 8i64, g_ptr));'''

content = content.replace(arr_handles_old, arr_handles_new)

with open('tests/test_query_ast/main.npk', 'w') as f:
    f.write(content)
