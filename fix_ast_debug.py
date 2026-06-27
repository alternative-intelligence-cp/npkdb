with open('tests/test_query_ast/main.npk', 'r') as f:
    content = f.read()

content = content.replace('println("Starting AST Query Filter Test...");', 'println("Starting AST Query Filter Test...");\n    println("1");')
content = content.replace('// {"year": {"$gt": 2020}}', 'println("2");\n    // {"year": {"$gt": 2020}}')
content = content.replace('// Array: [ y_obj, g_obj ]', 'println("3");\n    // Array: [ y_obj, g_obj ]')
content = content.replace('// Root {"$and": [...]}', 'println("4");\n    // Root {"$and": [...]}')
content = content.replace('// Parse AST', 'println("5");\n    // Parse AST')
content = content.replace('int64:arena = raw ast_arena_init(4096i64);', 'println("6");\n    int64:arena = raw ast_arena_init(4096i64);')
content = content.replace('if (ast_root == 0i64) {', 'println("7");\n    if (ast_root == 0i64) {')
content = content.replace('println("AST parsed successfully. Testing evaluator...");', 'println("8");\n    println("AST parsed successfully. Testing evaluator...");')

with open('tests/test_query_ast/main.npk', 'w') as f:
    f.write(content)

