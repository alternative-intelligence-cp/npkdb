import os
import re

dirs = ["/home/randy/Workspace/REPOS/npkdb/src", "/home/randy/Workspace/REPOS/npkdb/tests"]

for d in dirs:
    for root, _, files in os.walk(d):
        for file in files:
            if file.endswith(".npk"):
                path = os.path.join(root, file)
                with open(path, "r") as f:
                    code = f.read()
                
                # First, remove `?! ...` or `? ...` after sst_rec_* functions
                # Pattern: sst_rec_[a-z_]+\(.*?\) \?!?[^;\n]*
                code = re.sub(r'(sst_rec_[a-z_]+\([^)]*\))\s*\?!?[^;\n]+', r'\1', code)
                
                # Then, insert `raw ` before sst_rec_ if it's not already there
                # Also we might have drop(sst_rec_free(rec)), we want drop(raw sst_rec_free(rec))
                code = re.sub(r'(?<!raw\s)(sst_rec_[a-z_]+\()', r'raw \1', code)
                
                with open(path, "w") as f:
                    f.write(code)
