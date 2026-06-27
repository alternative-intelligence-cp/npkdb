import re

with open("src/query/evaluator.npk", "r") as f:
    content = f.read()

debug_prints2 = """        if (actual.type == JSON_NULL) {
            println("eval_path returned JSON_NULL!");
            last_result = 0i64;
            continue;
        }
        
        println("types:");
        println(@cast_unchecked<int64>(actual.type));
        println(@cast_unchecked<int64>(target.type));
        
        if (op == (@cast_unchecked<int64>(AST_OP_EQ))) {"""

content = content.replace("""        if (actual.type == JSON_NULL) {
            last_result = 0i64;
            continue;
        }
        
        if (op == (@cast_unchecked<int64>(AST_OP_EQ))) {""", debug_prints2)

with open("src/query/evaluator.npk", "w") as f:
    f.write(content)
