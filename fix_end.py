import re
filepath = 'tests/test_distance_props/main.npk'
with open(filepath, 'r') as f:
    content = f.read()

content = re.sub(
r'if \(pass_count < 40i64\).*',
r'''if (pass_count < 40i64) { exit 1i32; } else { exit 0i32; }
};

func:failsafe = int32(tbb32:err) {
    exit @cast_unchecked<int32>(err);
};''',
content, flags=re.DOTALL)

with open(filepath, 'w') as f:
    f.write(content)
