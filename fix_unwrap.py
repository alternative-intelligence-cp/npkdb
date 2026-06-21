import os, glob

files = glob.glob("src/vector/*.npk") + glob.glob("tests/test_hnsw_graph/*.npk")
for f in files:
    with open(f, 'r') as fp:
        code = fp.read()
    
    code = code.replace("npk_mem_read_int32(ep_slot_ptr, 0i64) ?! -1i32;", "npk_mem_read_int32(ep_slot_ptr, 0i64);")
    code = code.replace("npk_mem_read_int32(ep_gen_ptr, 0i64) ?! -1i32;", "npk_mem_read_int32(ep_gen_ptr, 0i64);")
    code = code.replace("npk_mem_read_int64(rand_state_ptr, 0i64) => uint64;", "@cast_unchecked<uint64>(npk_mem_read_int64(rand_state_ptr, 0i64));")
    
    # fix the ! on write
    code = code.replace("drop(npk_mem_write_float32", "drop(npk_mem_write_int32")
    code = code.replace("val));", "@cast_unchecked<int32>(val)));")
    
    with open(f, 'w') as fp:
        fp.write(code)

print("Done")
