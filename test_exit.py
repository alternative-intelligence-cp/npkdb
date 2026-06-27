with open('tests/test_query_ast/main.npk', 'r') as f:
    for line in f:
        if 'exit(' in line:
            print(line.strip())
