with open('tests/test_query_ast/main.npk', 'r') as f:
    content = f.read()

content = content.replace('    if (op == AST_OP_EQ) {',
                          '''    if (op == AST_OP_EQ) {
        println("EVAL AST_OP_EQ");
        println(string_from_int(cast_unchecked<int64>(actual.type)));
        println(string_from_int(cast_unchecked<int64>(target.type)));
        println(string_from_int(actual.payload));
        println(string_from_int(target.payload));''')

with open('tests/test_query_ast/main.npk', 'w') as f:
    f.write(content)
