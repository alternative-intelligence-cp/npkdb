import os
for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".npk"):
            path = os.path.join(root, file)
            with open(path, "r") as f:
                content = f.read()
            
            content = content.replace("func(int64)->int64:worker_fn", "(int64)(int64):worker_fn")
            
            with open(path, "w") as f:
                f.write(content)
