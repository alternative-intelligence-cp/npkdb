import os

old_str = """                    if (reader != 0i64) {
                        int64:rec = sstable_get(reader, key) ? 0i64;
                        drop(sstable_close_read(reader));
                        if (rec != 0i64) {
                            int64:is_ts = sst_rec_is_tombstone(rec) ? 0i64;
                            if (is_ts == 1i64) {
                                drop(sst_rec_free(rec));
                                if (sstables != 0i64) { drop(npk_core_dalloc(sstables)); }
                                pass("");
                            }
                            int64:vlen = sst_rec_val_len(rec) ? 0i64;
                            int64:vptr = sst_rec_val_ptr(rec) ? 0i64;
                            string:s = npk_mem_read_string(vptr, vlen);
                            drop(sst_rec_free(rec));
                            if (sstables != 0i64) { drop(npk_core_dalloc(sstables)); }
                            pass(s);
                        }
                    }"""

new_str = """                    if (reader != 0i64) {
                        int64:rec = sstable_get(reader, key) ? 0i64;
                        if (rec != 0i64) {
                            int64:is_ts = sst_rec_is_tombstone(rec) ? 0i64;
                            if (is_ts == 1i64) {
                                drop(sst_rec_free(rec));
                                if (sstables != 0i64) { drop(npk_core_dalloc(sstables)); }
                                drop(sstable_close_read(reader));
                                pass("");
                            }
                            int64:vlen = sst_rec_val_len(rec) ? 0i64;
                            int64:vptr = sst_rec_val_ptr(rec) ? 0i64;
                            string:s = npk_mem_read_string(vptr, vlen);
                            drop(sst_rec_free(rec));
                            if (sstables != 0i64) { drop(npk_core_dalloc(sstables)); }
                            drop(sstable_close_read(reader));
                            pass(s);
                        }
                        drop(sstable_close_read(reader));
                    }"""

for root, _, files in os.walk('tests'):
    for f in files:
        if f.endswith('.npk'):
            path = os.path.join(root, f)
            with open(path, 'r') as file:
                content = file.read()
            if old_str in content:
                content = content.replace(old_str, new_str)
                with open(path, 'w') as file:
                    file.write(content)
                print(f"Fixed {path}")
