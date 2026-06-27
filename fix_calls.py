import os
import re

for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".npk"):
            path = os.path.join(root, file)
            with open(path, "r") as f:
                content = f.read()
            
            # fix wp_init calls
            content = re.sub(r'wp_init\(([^,]+),\s*([^,]+),\s*@([a-zA-Z0-9_]+),\s*([^)]+)\)', r'wp_init(\1, \2, cast_unchecked<any->>(@\3), \4)', content)
            
            # fix compaction_worker_start calls
            content = re.sub(r'compaction_worker_start\(([^,]+),\s*@([a-zA-Z0-9_]+)\)', r'compaction_worker_start(\1, cast_unchecked<any->>(@\2))', content)
            
            # fix http_worker_start calls
            content = re.sub(r'http_worker_start\(([^,]+),\s*@([a-zA-Z0-9_]+)\)', r'http_worker_start(\1, cast_unchecked<any->>(@\2))', content)
            
            with open(path, "w") as f:
                f.write(content)
