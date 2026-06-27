with open('tests/test_query_ast/main.npk', 'r') as f:
    content = f.read()

content = content.replace('drop(npk_mem_write_int32(obj, 0i64, cast_unchecked<int64>(len)));', 'drop(npk_mem_write_int32(obj, 0i64, cast_unchecked<int32>(len)));')
content = content.replace('int64:ast_root = raw parse_filter(arena, query, 0i32);', 'int64:ast_root = raw parse_filter(arena, query.payload, 0i32);')
content = content.replace('bool:match = raw eval_ast(ast_root, doc);', 'bool:match = raw eval_ast(ast_root, doc.payload);')

with open('tests/test_query_ast/main.npk', 'w') as f:
    f.write(content)
