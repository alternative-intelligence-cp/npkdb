with open('controllers_mock.npk', 'r') as f:
    lines = f.readlines()

with open('controllers_mock.npk', 'w') as f:
    for line in lines:
        if 'nitpick_libc_rwlock' in line and 'global_graph_lock' in line:
            continue
        f.write(line)
