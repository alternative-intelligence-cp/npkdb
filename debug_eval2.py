with open('tests/test_query_ast/main.npk', 'r') as f:
    content = f.read()

content = content.replace('func:eval_ast = bool(int64:node_ptr, int64:doc_ptr) {',
                          '''func:eval_ast = bool(int64:node_ptr, int64:doc_ptr) {
    println("EVAL_AST called with op:");
    int64:op = cast_unchecked<int64>(npk_mem_read_byte(node_ptr, 0i64));
    println(string_from_int(op));''')

with open('tests/test_query_ast/main.npk', 'w') as f:
    f.write(content)
