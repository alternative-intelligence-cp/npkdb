with open('src/query/filter_parser.npk', 'r') as f:
    content = f.read()

content = content.replace('if (k0_elem.type != JSON_STR) { pass(0i64); }',
                          'println("P6");\n    if (k0_elem.type != JSON_STR) { println("P6-FAIL"); pass(0i64); }')

content = content.replace('if (raw streq(k0_str_ptr, "$and") || raw streq(k0_str_ptr, "$or")) {',
                          'println("P7");\n    if (raw streq(k0_str_ptr, "$and") || raw streq(k0_str_ptr, "$or")) {')

content = content.replace('if (v0_elem.type != JSON_ARR) { pass(0i64); }',
                          'println("P8");\n        if (v0_elem.type != JSON_ARR) { println("P8-FAIL"); pass(0i64); }')

content = content.replace('int64:children_ptr = raw ast_arena_alloc(arena_ptr, arr_count * 8i64);',
                          'println("P9");\n        int64:children_ptr = raw ast_arena_alloc(arena_ptr, arr_count * 8i64);')

with open('src/query/filter_parser.npk', 'w') as f:
    f.write(content)
