with open('tests/test_query_ast/main.npk', 'r') as f:
    content = f.read()

content = content.replace('int64:arena = raw ast_arena_init(4096i64);', 'println("Allocating arena");\n    int64:arena = raw ast_arena_init(4096i64);\n    println("Arena allocated");')
content = content.replace('int64:ast_root = raw parse_filter(arena, query.payload, 0i32);', 'println("Parsing filter");\n    int64:ast_root = raw parse_filter(arena, query.payload, 0i32);\n    println("Filter parsed");')

with open('tests/test_query_ast/main.npk', 'w') as f:
    f.write(content)
