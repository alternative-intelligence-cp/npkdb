import os
import re

for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".npk"):
            path = os.path.join(root, file)
            with open(path, "r") as f:
                content = f.read()
            
            # fix wp_init definition
            content = content.replace("wild any->:worker_fn", "func(int64)->int64:worker_fn")
            
            # fix server_start definition
            content = content.replace("wild any->:worker_fn", "func(int64)->int64:worker_fn")

            # fix http_worker_start definition
            content = content.replace("wild any->:worker_fn", "func(int64)->int64:worker_fn")
            
            # fix compaction_worker_start definition
            content = content.replace("wild any->:worker_fn", "func(int64)->int64:worker_fn")
            
            # fix nitpick_libc_thread_spawn calls inside them
            content = content.replace("cast_unchecked<any->>(worker_fn)", "worker_fn")
            
            # fix the callers (we previously added cast_unchecked<any->>(@...))
            content = re.sub(r'cast_unchecked<any->>\(@([a-zA-Z0-9_]+)\)', r'@\1', content)
            
            with open(path, "w") as f:
                f.write(content)
