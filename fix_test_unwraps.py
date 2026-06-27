import os
import re

for root, _, files in os.walk('tests'):
    for file in files:
        if file.endswith('.npk'):
            filepath = os.path.join(root, file)
            with open(filepath, "r") as f:
                content = f.read()

            content = re.sub(r'int64:fwd\s*=\s*sl_node_forward\(curr,\s*lvl\);', r'int64:fwd = sl_node_forward(curr, lvl) ? 0i64;', content)
            content = re.sub(r'int64:cand\s*=\s*sl_node_forward\(curr,\s*0i64\);', r'int64:cand = sl_node_forward(curr, 0i64) ? 0i64;', content)
            content = re.sub(r'int64:active_mt\s*=\s*wp_active_memtable\(wp\);', r'int64:active_mt = wp_active_memtable(wp) ? 0i64;', content)
            content = re.sub(r'int64:frozen_mt\s*=\s*wp_frozen_memtable\(wp\);', r'int64:frozen_mt = wp_frozen_memtable(wp) ? 0i64;', content)
            content = re.sub(r'int64:lm\s*=\s*wp_level_manager\(wp\);', r'int64:lm = wp_level_manager(wp) ? 0i64;', content)
            content = re.sub(r'int64:wp1\s*=\s*wp_init\(([^)]+)\);', r'int64:wp1 = wp_init(\1) ? 0i64;', content)
            content = re.sub(r'int64:node\s*=\s*test_mt_get_node\(([^)]+)\);', r'int64:node = test_mt_get_node(\1) ? 0i64;', content)
            content = re.sub(r'int64:is_del1\s*=\s*sl_node_is_deleted\(([^)]+)\);', r'int64:is_del1 = sl_node_is_deleted(\1) ? 0i64;', content)
            content = re.sub(r'int64:val_len1\s*=\s*sl_node_val_len\(([^)]+)\);', r'int64:val_len1 = sl_node_val_len(\1) ? 0i64;', content)
            content = re.sub(r'int64:vptr1\s*=\s*sl_node_val_ptr\(([^)]+)\);', r'int64:vptr1 = sl_node_val_ptr(\1) ? 0i64;', content)
            content = re.sub(r'int64:is_del2\s*=\s*sl_node_is_deleted\(([^)]+)\);', r'int64:is_del2 = sl_node_is_deleted(\1) ? 0i64;', content)
            content = re.sub(r'int64:val_len2\s*=\s*sl_node_val_len\(([^)]+)\);', r'int64:val_len2 = sl_node_val_len(\1) ? 0i64;', content)
            content = re.sub(r'int64:vptr2\s*=\s*sl_node_val_ptr\(([^)]+)\);', r'int64:vptr2 = sl_node_val_ptr(\1) ? 0i64;', content)
            content = re.sub(r'int64:is_del\s*=\s*sl_node_is_deleted\(([^)]+)\);', r'int64:is_del = sl_node_is_deleted(\1) ? 0i64;', content)
            content = re.sub(r'int64:val_len\s*=\s*sl_node_val_len\(([^)]+)\);', r'int64:val_len = sl_node_val_len(\1) ? 0i64;', content)
            content = re.sub(r'int64:vptr\s*=\s*sl_node_val_ptr\(([^)]+)\);', r'int64:vptr = sl_node_val_ptr(\1) ? 0i64;', content)
            content = re.sub(r'int64:sst_fwd\s*=\s*lm_sstable_forward\(([^)]+)\);', r'int64:sst_fwd = lm_sstable_forward(\1) ? 0i64;', content)
            content = re.sub(r'int64:sst\s*=\s*lm_sstable_forward\(([^)]+)\);', r'int64:sst = lm_sstable_forward(\1) ? 0i64;', content)

            with open(filepath, "w") as f:
                f.write(content)
