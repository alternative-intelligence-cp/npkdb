import re

with open("src/query/evaluator.npk", "r") as f:
    text = f.read()

# Fix astack
text = text.replace("int64:st = astack(2048i64);", "astack 2048i64;")

# Fix apush
text = re.sub(r'drop\(apush\(st,\s*(.*?)\)\);', r'apush(\1);', text)

# Fix apop
text = text.replace("apop(st)", "apop()")

with open("src/query/evaluator.npk", "w") as f:
    f.write(text)
