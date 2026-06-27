import os
import re

for root, _, files in os.walk("/home/randy/Workspace/REPOS/npkdb/src"):
    for file in files:
        if file.endswith(".npk"):
            path = os.path.join(root, file)
            with open(path, "r") as f:
                code = f.read()
            code = re.sub(r'sst_rec_key\(([^)]+)\)\s*\?!?\s*""', r'sst_rec_key(\1)', code)
            with open(path, "w") as f:
                f.write(code)
