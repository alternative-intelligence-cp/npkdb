import os

dirs_to_search = ["src", "tests"]
for d in dirs_to_search:
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith(".npk"):
                path = os.path.join(root, f)
                with open(path, "r") as src:
                    content = src.read()
                
                new_content = content.replace("@cast_unchecked", "cast_unchecked")
                new_content = new_content.replace("@cast", "cast")
                
                if new_content != content:
                    with open(path, "w") as out:
                        out.write(new_content)
                    print(f"Fixed casts in {path}")
