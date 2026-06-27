import os
import re

for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".npk"):
            path = os.path.join(root, file)
            with open(path, "r") as f:
                content = f.read()
            
            content = re.sub(r'server_start\(@([a-zA-Z0-9_]+)\)', r'server_start(cast_unchecked<any->>(@\1))', content)
            
            with open(path, "w") as f:
                f.write(content)
