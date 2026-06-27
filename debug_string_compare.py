with open('src/query/filter_parser.npk', 'r') as f:
    content = f.read()

content = content.replace('if (res != 0i64) { pass(false); }',
                          '''if (res != 0i64) {
        println("STREQ MISMATCH!");
        println(string_from_int(b_len));
        
        int64:i = 0i64;
        while (i < b_len) {
            println(string_from_int(cast_unchecked<int64>(npk_mem_read_byte(a_ptr, i))));
            println(string_from_int(cast_unchecked<int64>(npk_mem_read_byte(b_data, i))));
            i = i + 1i64;
        }
        pass(false);
    }''')

with open('src/query/filter_parser.npk', 'w') as f:
    f.write(content)
