import os
import glob

test_dir = "/home/randy/Workspace/REPOS/npkdb/tests"
files = glob.glob(os.path.join(test_dir, "**/*.npk"), recursive=True)

for file in files:
    with open(file, 'r') as f:
        content = f.read()
    
    new_content = content.replace('nitpick_libc_mem_malloc', 'npk_core_alloc')
    new_content = new_content.replace('nitpick_libc_mem_free', 'npk_core_dalloc')
    new_content = new_content.replace('extern "nitpick_libc_mem" {\n    func:npk_core_alloc = int64(int64:size);\n    func:npk_core_dalloc = void(int64:ptr);\n}', '')
    new_content = new_content.replace('extern "nitpick_libc_mem" {\n    func:nitpick_libc_mem_malloc = int64(int64:size);\n    func:nitpick_libc_mem_free = void(int64:ptr);\n}', '')
    
    if new_content != content:
        with open(file, 'w') as f:
            f.write(new_content)
        print(f"Fixed {file}")

