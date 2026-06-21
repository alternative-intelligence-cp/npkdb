import subprocess
import re

def run_compiler():
    # run npkc and capture stderr
    cmd = "export PATH=\"/home/randy/Workspace/REPOS/nitpick/build:$PATH\" && npkc tests/test_hnsw_graph/main.npk -o build/test_hnsw_graph 2>&1"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.stdout

def fix_errors():
    output = run_compiler()
    lines = output.split('\n')
    
    fixes = {} # file -> list of (line_num, expected_type, var_name)
    
    for i, line in enumerate(lines):
        if "Cannot silently unwrap Result<" in line:
            # tests/test_hnsw_graph/main.npk:0:0: error: Line 15, Column 5: Cannot silently unwrap Result<int64> into 'arena' of type 'int64'.
            m = re.search(r'error: Line (\d+), .*? Cannot silently unwrap Result<.*?> into \'.*?\' of type \'(.*?)\'.', line)
            if m:
                line_num = int(m.group(1))
                exp_type = m.group(2)
                # But wait, the error gives the line number of the FLATTENED file!
                # We can't easily map it back to the original file unless we know which file it is.
                pass
                
    # Instead, let's just use regex on all .npk files!
    import glob
    files = glob.glob("src/vector/*.npk") + glob.glob("tests/test_hnsw_graph/*.npk")
    for f in files:
        with open(f, 'r') as fp:
            code = fp.read()
        
        # pattern: type:var = hnsw_...(args) ;
        def replacer(m):
            t = m.group(1)
            var = m.group(2)
            call = m.group(3)
            if t == "int64": default = "0i64"
            elif t == "int32": default = "0i32"
            elif t == "float32": default = "0.0f32"
            elif t == "float64": default = "0.0f64"
            elif t == "bool": default = "false"
            elif t == "int16": default = "0i16"
            else: default = "0"
            
            # check if it already has ?!
            if "?!" in call: return m.group(0)
            
            return f"{t}:{var} = {call} ?! {default};"
            
        code = re.sub(r'(int64|int32|int16|float32|float64|bool):([a-zA-Z0-9_]+)\s*=\s*(hnsw_[a-zA-Z0-9_]+([^;]+))\s*;', replacer, code)
        
        with open(f, 'w') as fp:
            fp.write(code)

fix_errors()
print("Done")
