with open("src/storage/sstable_io.npk", "r") as f:
    text = f.read()

target1 = """    int64:last_k_ptr_dup = npk_core_alloc(last_k_len);
    drop(npk_mem_copy(last_k_ptr_dup, last_k_ptr_src, last_k_len));"""
replace1 = """    int64:last_k_ptr_dup = 0i64;
    if (last_k_len > 0i64) {
        last_k_ptr_dup = npk_core_alloc(last_k_len);
        drop(npk_mem_copy(last_k_ptr_dup, last_k_ptr_src, last_k_len));
    }"""

target2 = """        drop(npk_mem_write_int32(rec, 0i64, @cast_unchecked<int32>(k_len)));
        drop(npk_mem_copy(rec + 4i64, k_ptr, k_len));
        drop(npk_mem_write_int64(rec, 4i64 + k_len, b_off));"""
replace2 = """        drop(npk_mem_write_int32(rec, 0i64, @cast_unchecked<int32>(k_len)));
        if (k_len > 0i64) {
            drop(npk_mem_copy(rec + 4i64, k_ptr, k_len));
        }
        drop(npk_mem_write_int64(rec, 4i64 + k_len, b_off));"""

text = text.replace(target1, replace1)
text = text.replace(target2, replace2)

with open("src/storage/sstable_io.npk", "w") as f:
    f.write(text)
