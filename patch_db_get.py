import re
with open('tests/test_integration/test_stress.npk', 'r') as fp:
    code = fp.read()
def repl(match):
    return '''    println("db_get: sstables");
    int64:lm = wp_level_manager(wp) ?! 1i64;
    if (lm != 0i64) {
        int64:lvl = 0i64;
        while (lvl < 5i64) {
            int64:sstables = lm_get_sstables(lm, lvl) ?! 1i64;
            if (sstables != 0i64) {
                int64:count = lm_count_at_level(lm, lvl) ?! 1i64;
                int64:i = 0i64;
                while (i < count) {
                    int64:idx = i;
                    if (lvl == 0i64) { idx = count - 1i64 - i; }
                    int64:fid = npk_mem_read_int64(sstables, idx * 8i64);
                    string:fid_str = string_from_int(fid);
                    while (string_length(fid_str) < 6i64) { fid_str = "0" + fid_str; }
                    string:spath = "test_stress/L" + string_from_int(lvl) + "/sst_" + fid_str + ".npkdb";
                    println("db_get: sstable_open_read " + spath);
                    int64:reader = sstable_open_read(spath) ?! 1i64;
                    println("db_get: sstable_open_read returned " + string_from_int(reader));
                    if (reader != 0i64) {
                        println("db_get: sstable_get");
                        int64:rec = sstable_get(reader, key) ?! 1i64;
                        println("db_get: sstable_close_read");
                        drop(sstable_close_read(reader));
                        if (rec != 0i64) {
                            println("db_get: is_ts");
                            int64:is_ts = sst_rec_is_tombstone(rec) ?! 1i64;
                            if (is_ts == 1i64) {
                                drop(sst_rec_free(rec));
                                if (sstables != 0i64) { drop(npk_core_dalloc(sstables)); }
                                pass("");
                            }
                            println("db_get: vlen");
                            int64:vlen = sst_rec_val_len(rec) ?! 1i64;
                            println("db_get: vptr");
                            int64:vptr = sst_rec_val_ptr(rec) ?! 1i64;
                            println("db_get: read_string " + string_from_int(vptr) + " " + string_from_int(vlen));
                            string:s = npk_mem_read_string(vptr, vlen);
                            println("db_get: sst_rec_free");
                            drop(sst_rec_free(rec));
                            if (sstables != 0i64) { drop(npk_core_dalloc(sstables)); }
                            pass(s);
                        }
                    }
                    i = i + 1i64;
                }
            }
            if (sstables != 0i64) { drop(npk_core_dalloc(sstables)); }
            lvl = lvl + 1i64;
        }
    }
'''

code = re.sub(r'    println\("db_get: sstables"\);.*?    if \(lm != 0i64\) \{.*?        \}\n    \}\n', repl, code, flags=re.DOTALL)
with open('tests/test_integration/test_stress.npk', 'w') as fp:
    fp.write(code)
