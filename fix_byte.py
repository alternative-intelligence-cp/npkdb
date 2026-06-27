with open('tests/test_query_ast/main.npk', 'r') as f:
    lines = f.readlines()

with open('tests/test_query_ast/main.npk', 'w') as f:
    for line in lines:
        line = line.replace('npk_mem_write_bytecast_unchecked<int64>(', 'npk_mem_write_byte(')
        line = line.replace('npk_mem_read_bytecast_unchecked<int8>(', 'npk_mem_read_byte(')
        line = line.replace('npk_mem_write_bytecast_unchecked<int8>(', 'npk_mem_write_byte(')
        line = line.replace('npk_mem_read_bytecast_unchecked<int64>(', 'npk_mem_read_byte(')
        f.write(line)

