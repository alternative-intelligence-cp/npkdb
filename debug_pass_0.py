with open('src/query/filter_parser.npk', 'r') as f:
    content = f.read()

content = content.replace('pass(0i64)', 'pass_zero()')

with open('src/query/filter_parser.npk', 'w') as f:
    f.write('''func:pass_zero = int64() {
    println("parse_filter returned 0!");
    pass(0i64);
};
''' + content)
