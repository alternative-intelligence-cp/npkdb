import re
import glob

def get_dir(fname):
    if "roundtrip" in fname: return "test_data_rt"
    if "compaction_correctness" in fname: return "test_comp_corr"
    if "stress" in fname: return "test_stress"
    return "unknown"

for fname in ["test_roundtrip.npk", "test_compaction_correctness.npk", "test_stress.npk"]:
    with open(fname, "r") as f:
        content = f.read()

    # Find where db_get starts and where pub func:main starts
    start_idx = content.find("func:db_get = string")
    end_idx = content.find("pub func:main = int32")
    
    if start_idx == -1 or end_idx == -1:
        print("Could not find db_get or main in", fname)
        continue

    dname = get_dir(fname)

    new_db_get = f"""func:db_get = string(int64:wp, string:key) {{
    // 1. Active Memtable
    int64:active_mt = wp_active_memtable(wp) ? 0i64;
    if (active_mt != 0i64) {{
        int64:node = test_mt_get_node(active_mt, key) ? 0i64;
        if (node != 0i64) {{
            int64:is_del1 = sl_node_is_deleted(node) ? 0i64;
            if (is_del1 == 1i64) {{ pass(""); }}
            int64:val_len1 = sl_node_val_len(node) ? 0i64;
            int64:vptr1 = sl_node_val_ptr(node) ? 0i64;
            pass(npk_mem_read_string(vptr1, val_len1));
        }}
    }}
    
    // 2. Frozen Memtable
    int64:frozen_mt = wp_frozen_memtable(wp) ? 0i64;
    if (frozen_mt != 0i64) {{
        int64:node = test_mt_get_node(frozen_mt, key) ? 0i64;
        if (node != 0i64) {{
            int64:is_del2 = sl_node_is_deleted(node) ? 0i64;
            if (is_del2 == 1i64) {{ pass(""); }}
            int64:val_len2 = sl_node_val_len(node) ? 0i64;
            int64:vptr2 = sl_node_val_ptr(node) ? 0i64;
            pass(npk_mem_read_string(vptr2, val_len2));
        }}
    }}
    
    // 3. SSTables
    int64:lm = wp_level_manager(wp) ? 0i64;
    if (lm != 0i64) {{
        int64:lvl = 0i64;
        while (lvl < 5i64) {{
            int64:sstables = lm_get_sstables(lm, lvl) ? 0i64;
            if (sstables != 0i64) {{
                int64:count = lm_count_at_level(lm, lvl) ? 0i64;
                int64:i = 0i64;
                while (i < count) {{
                    int64:idx = i;
                    if (lvl == 0i64) {{ idx = count - 1i64 - i; }}
                    int64:fid = npk_mem_read_int64(sstables, idx * 8i64);
                    
                    string:fid_str = string_from_int(fid);
                    while (string_length(fid_str) < 6i64) {{
                        fid_str = "0" + fid_str;
                    }}
                    string:spath1 = "{dname}/L" + string_from_int(lvl);
                    string:spath2 = spath1 + "/sst_";
                    string:spath3 = spath2 + fid_str;
                    string:spath = spath3 + ".npkdb";
                    
                    int64:reader = sstable_open_read(spath) ? 0i64;
                    if (reader != 0i64) {{
                        int64:rec = sstable_get(reader, key) ? 0i64;
                        if (rec != 0i64) {{
                            int64:is_ts = sst_rec_is_tombstone(rec) ? 0i64;
                            if (is_ts == 1i64) {{
                                drop(sst_rec_free(rec));
                                drop(sstable_close_read(reader));
                                if (sstables != 0i64) {{ drop(npk_core_dalloc(sstables)); }}
                                pass("");
                            }}
                            int64:val_len_r = sst_rec_val_len(rec) ? 0i64;
                            int64:vptr3 = sst_rec_val_ptr(rec) ? 0i64;
                            string:val_str = npk_mem_read_string(vptr3, val_len_r);
                            drop(sst_rec_free(rec));
                            drop(sstable_close_read(reader));
                            if (sstables != 0i64) {{ drop(npk_core_dalloc(sstables)); }}
                            pass(val_str);
                        }}
                        drop(sstable_close_read(reader));
                    }}
                    i = i + 1i64;
                }}
                drop(npk_core_dalloc(sstables));
            }}
            lvl = lvl + 1i64;
        }}
    }}
    pass("");
}};

"""

    content = content[:start_idx] + new_db_get + content[end_idx:]
    with open(fname, "w") as f:
        f.write(content)
    print("Rewrote", fname)

