import os
for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".npk"):
            path = os.path.join(root, file)
            with open(path, "r") as f:
                content = f.read()
            if "req->" in content:
                content = content.replace("req->", "req.")
                with open(path, "w") as f:
                    f.write(content)
