with open('tests/test_query_ast/main.npk', 'r') as f:
    lines = f.read().split('\n')

out_lines = []
print_counter = 4
for line in lines:
    out_lines.append(line)
    if 'make_json_str(' in line and 'func:' not in line:
        out_lines.append(f'    println("{print_counter}");')
        print_counter += 1
    elif 'ast_arena_init' in line and 'func:' not in line:
        out_lines.append(f'    println("ARENA");')
    elif 'parse_filter' in line and 'func:' not in line:
        out_lines.append(f'    println("PARSE_FILTER");')

with open('tests/test_query_ast/main.npk', 'w') as f:
    f.write('\n'.join(out_lines))
