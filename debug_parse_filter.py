with open('src/query/filter_parser.npk', 'r') as f:
    content = f.read()

content = content.replace('    pass(node_ptr);',
                          '''    println("PARSE FILTER RETURNING NODE:");
    println(string_from_int(node_ptr));
    println("OP:");
    println(string_from_int(cast_unchecked<int64>(npk_mem_read_byte(node_ptr, 0i64))));
    pass(node_ptr);''')

with open('src/query/filter_parser.npk', 'w') as f:
    f.write(content)
