with open('tests/test_query_ast/main.npk', 'r') as f:
    content = f.read()

content = content.replace('int8:root_op = npk_mem_read_byte(ast_root, 0i64);', 'int8:root_op = cast_unchecked<int8>(npk_mem_read_byte(ast_root, 0i64));')

with open('tests/test_query_ast/main.npk', 'w') as f:
    f.write(content)
