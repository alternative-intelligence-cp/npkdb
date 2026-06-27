import sys

# Replace the printlns with more debug info to see if it even reaches ast_root
with open('tests/test_query_ast/main.npk', 'r') as f:
    lines = f.readlines()

with open('tests/test_query_ast/main.npk', 'w') as f:
    for line in lines:
        if 'if (ast_root == 0i64) {' in line:
            f.write('    println("AST_ROOT is: ");\n')
            f.write('    println(string_from_int(ast_root));\n')
            f.write(line)
        else:
            f.write(line)

