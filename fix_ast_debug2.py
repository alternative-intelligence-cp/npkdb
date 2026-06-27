with open('tests/test_query_ast/main.npk', 'r') as f:
    content = f.read()

content = content.replace('int64:arena = raw ast_arena_init(4096i64);', 'int64:arena = raw ast_arena_init(4096i64);\n    println("6.5");')

with open('tests/test_query_ast/main.npk', 'w') as f:
    f.write(content)

