with open('src/query/filter_parser.npk', 'r') as f:
    content = f.read()

content = content.replace('println("STREQ FAIL: res != 0");',
                          'println("STREQ FAIL: res != 0");\n        println(string_from_int(cast_unchecked<int64>(npk_mem_read_byte(a_ptr, 0i64))));\n        println(string_from_int(cast_unchecked<int64>(npk_mem_read_byte(cast_unchecked<int64>(b), 0i64))));')

with open('src/query/filter_parser.npk', 'w') as f:
    f.write(content)
