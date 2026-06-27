import re
import os

with open("/home/randy/Workspace/META/NPKDB/audits/a21/audit.md", "r") as f:
    audit = f.read()

# Directive 1
d1_match = re.search(r'pub func:controller_insert.*?pub func:controller_search.*?^};', audit, re.MULTILINE | re.DOTALL)
if d1_match:
    d1_code = d1_match.group(0)
    with open("src/network/controllers.npk", "r") as f:
        controllers = f.read()
    controllers = re.sub(r'pub func:controller_insert.*?^};(\n\n)?pub func:controller_search.*?^};', d1_code, controllers, flags=re.MULTILINE | re.DOTALL)
    with open("src/network/controllers.npk", "w") as f:
        f.write(controllers)
    print("Directive 1 applied.")
else:
    print("Could not find Directive 1 code in audit.md")

# Directive 2
d2_match = re.search(r'pub func:evaluate_filter.*?^};', audit[audit.find('DIRECTIVE 2'):], re.MULTILINE | re.DOTALL)
if d2_match:
    d2_code = d2_match.group(0)
    with open("src/query/evaluator.npk", "r") as f:
        evaluator = f.read()
    evaluator = re.sub(r'pub func:evaluate_filter.*?^};', d2_code, evaluator, flags=re.MULTILINE | re.DOTALL)
    with open("src/query/evaluator.npk", "w") as f:
        f.write(evaluator)
    print("Directive 2 applied.")
else:
    print("Could not find Directive 2 code in audit.md")

# Directive 4
d4_code = """    NpkJsonVal:k0_elem = NpkJsonVal {  
        type: cast_unchecked<int8>(npk_mem_read_byte(key0_ptr, 0i64)),  
        payload: npk_mem_read_int64(key0_ptr, 8i64)  
    };"""
with open("src/query/filter_parser.npk", "r") as f:
    filter_parser = f.read()

# Let's see how NpkJsonVal:k0_elem is currently defined
fp_match = re.search(r'NpkJsonVal:k0_elem = NpkJsonVal \{.*?\};', filter_parser, re.MULTILINE | re.DOTALL)
if fp_match:
    filter_parser = filter_parser.replace(fp_match.group(0), d4_code)
    with open("src/query/filter_parser.npk", "w") as f:
        f.write(filter_parser)
    print("Directive 4 applied.")
else:
    print("Could not find k0_elem in filter_parser.npk")

# Directive 3 - Global replace @cast_unchecked
for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".npk"):
            path = os.path.join(root, file)
            with open(path, "r") as f:
                content = f.read()
            if "@cast_unchecked" in content:
                content = content.replace("@cast_unchecked", "cast_unchecked")
                with open(path, "w") as f:
                    f.write(content)
                print(f"Replaced @cast_unchecked in {path}")

# Directive 3 - Update thread signatures
def replace_in_file(filepath, old, new):
    with open(filepath, "r") as f:
        content = f.read()
    if old in content:
        content = content.replace(old, new)
        with open(filepath, "w") as f:
            f.write(content)
        print(f"Updated signature in {filepath}")
    else:
        print(f"Could not find '{old}' in {filepath}")

replace_in_file("src/storage/write_path.npk", 
    "pub func:wp_init = int64(string:data_dir, string:wal_path, wild ?->:worker_fn, string:sync_mode)",
    "pub func:wp_init = int64(string:data_dir, string:wal_path, wild any->:worker_fn, string:sync_mode)")

replace_in_file("src/storage/compaction_worker.npk",
    "pub func:compaction_worker_start = int64(int64:lm, wild ?->:worker_fn)",
    "pub func:compaction_worker_start = int64(int64:lm, wild any->:worker_fn)")
replace_in_file("src/storage/compaction_worker.npk",
    "int64:tid = nitpick_libc_thread_spawn(worker_fn, ctx);",
    "int64:tid = nitpick_libc_thread_spawn(cast_unchecked<wild any->>(worker_fn), ctx);")

replace_in_file("src/network/server.npk",
    "pub func:server_start = int32(wild ?->:worker_fn)",
    "pub func:server_start = int32(wild any->:worker_fn)")

replace_in_file("src/network/http_worker.npk",
    "pub func:http_worker_start = int64(int64:ch, wild ?->:worker_fn)",
    "pub func:http_worker_start = int64(int64:ch, wild any->:worker_fn)")
replace_in_file("src/network/http_worker.npk",
    "pass nitpick_libc_thread_spawn(worker_fn, ch);",
    "pass nitpick_libc_thread_spawn(cast_unchecked<wild any->>(worker_fn), ch);")

