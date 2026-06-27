import os
for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".npk"):
            path = os.path.join(root, file)
            with open(path, "r") as f:
                content = f.read()
            if "cast_unchecked<wild any->" in content:
                content = content.replace("cast_unchecked<wild any->", "cast_unchecked<any->")
                with open(path, "w") as f:
                    f.write(content)
