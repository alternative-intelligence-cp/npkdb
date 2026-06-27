with open('controllers_mock.npk', 'r') as f:
    lines = f.readlines()

with open('controllers_mock.npk', 'w') as f:
    for line in lines:
        if 'drop(nitpick_libc_rwlock' in line:
            continue
        f.write(line)
