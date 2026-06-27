with open('tests/test_query_ast/main.npk', 'r') as f:
    content = f.read()

content = content.replace('NpkJsonVal:target = NpkJsonVal {', 'NpkJsonVal:target = NpkJsonVal {\n        type: cast_unchecked<int8>(npk_mem_read_byte(node_ptr, 16i64)),')
content = content.replace('type: npk_mem_read_byte(node_ptr, 16i64),', '')
content = content.replace('parse_filter(arena, cast_unchecked<int64>(@query));', 'parse_filter(arena, cast_unchecked<int64>(@query), 0i32);')

with open('tests/test_query_ast/main.npk', 'w') as f:
    f.write(content)
