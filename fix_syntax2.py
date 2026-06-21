import os, glob

files = glob.glob("tests/test_hnsw_graph/*.npk")
for f in files:
    with open(f, 'r') as fp:
        code = fp.read()
    
    code = code.replace("?! 0i64;", ";")
    code = code.replace("?! 0i32;", ";")
    code = code.replace("?! 0.0f64;", ";")
    code = code.replace("?! 0.0f32;", ";")
    code = code.replace("?! -1i32;", ";")
    code = code.replace("?! -1i64;", ";")
    code = code.replace("?! -1.0f32;", ";")
    
    with open(f, 'w') as fp:
        fp.write(code)

print("Done")
