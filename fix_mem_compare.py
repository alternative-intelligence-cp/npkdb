import os
for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".npk"):
            path = os.path.join(root, file)
            with open(path, "r") as f:
                content = f.read()
            if "raw npk_mem_compare" in content:
                content = content.replace("raw npk_mem_compare", "npk_mem_compare")
                with open(path, "w") as f:
                    f.write(content)
