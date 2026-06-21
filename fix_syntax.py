import os, glob

files = glob.glob("src/vector/*.npk")
for f in files:
    with open(f, 'r') as fp:
        code = fp.read()
    
    # Fix pub const NAME:int64 to pub fixed int64:NAME
    import re
    code = re.sub(r'pub const ([A-Z0-9_]+):(int64|int32|float32|float64)\s*=', r'pub fixed \2:\1 =', code)
    code = re.sub(r'pub const ([A-Z0-9_]+): ([int64|int32|float32|float64]+)\s*=', r'pub fixed \2:\1 =', code)
    
    # Also clean up ?! that I missed
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
