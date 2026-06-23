import re

files = ['src/vector/hnsw_search.npk', 'src/vector/hnsw_insert.npk']
for file in files:
    with open(file, 'r') as f:
        content = f.read()

    # Remove all '? ...' default unwrap syntax because these functions do not return Result!
    # e.g., ' ? 0i64', ' ? 0.0f64', '? 100i32', ' ? 3.402823466e+38tf'
    content = re.sub(r'\s*\?\s*[0-9\.\-e\+]+(?:i64|i32|i16|i8|u64|u32|u16|u8|f64|f32|tf)', '', content)
    
    with open(file, 'w') as f:
        f.write(content)

print("hnsw files fixed")
