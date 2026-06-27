with open('tests/test_query_ast/main.npk', 'r') as f:
    content = f.read()

content = content.replace('println("Expected $and root node");',
                          'println("Expected $and root node");\n        println(string_from_int(cast_unchecked<int64>(root_op)));')

with open('tests/test_query_ast/main.npk', 'w') as f:
    f.write(content)
