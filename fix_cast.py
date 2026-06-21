import os, glob

files = glob.glob("src/vector/*.npk") + glob.glob("tests/test_hnsw_graph/*.npk")
for f in files:
    with open(f, 'r') as fp:
        code = fp.read()
    
    code = code.replace("@cast_unchecked<uint64>(npk_mem_read_int64(rand_state_ptr, 0i64))", "(npk_mem_read_int64(rand_state_ptr, 0i64) => uint64)")
    code = code.replace("@cast_unchecked<float64>(r_int)", "(r_int => float64)")
    code = code.replace("@cast_unchecked<int32>(math_floor(l_val))", "(math_floor(l_val) => int32)")
    
    # Also in tests/test_hnsw_graph/main.npk
    code = code.replace("@cast_unchecked<float32>(next_s % 100i64)", "((next_s % 100i64) => float32)")
    code = code.replace("@cast_unchecked<int32>(val)", "(val => int32)")
    code = code.replace("@cast_unchecked<int32>(err)", "(err => int32)")
    
    with open(f, 'w') as fp:
        fp.write(code)

print("Done")
