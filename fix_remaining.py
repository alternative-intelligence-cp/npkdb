import re

# 1. Fix hnsw_search.npk: !raw
with open('src/vector/hnsw_search.npk', 'r') as f:
    content = f.read()

content = content.replace('!raw hnsw_visited_check', '!(raw hnsw_visited_check')
# Add the missing closing parenthesis. The regex will find `!(raw hnsw_visited_check(X, Y)` and add `)` at the end of the call.
content = re.sub(r'!\(raw hnsw_visited_check\(([^)]+)\)', r'!(raw hnsw_visited_check(\1))', content)

with open('src/vector/hnsw_search.npk', 'w') as f:
    f.write(content)

# 2. Fix hnsw_insert.npk: hnsw_search_layer -> raw hnsw_search_layer
with open('src/vector/hnsw_insert.npk', 'r') as f:
    content = f.read()

content = re.sub(r'(?<!raw )\bhnsw_search_layer\(', r'raw hnsw_search_layer(', content)
content = re.sub(r'(?<!raw )\bhnsw_select_neighbors\(', r'raw hnsw_select_neighbors(', content)

with open('src/vector/hnsw_insert.npk', 'w') as f:
    f.write(content)

# 3. Fix controllers.npk: hnsw_search_layer -> raw hnsw_search_layer
with open('src/network/controllers.npk', 'r') as f:
    content = f.read()

content = re.sub(r'(?<!raw )\bhnsw_search_layer\(', r'raw hnsw_search_layer(', content)

with open('src/network/controllers.npk', 'w') as f:
    f.write(content)

print("remaining fixed")
