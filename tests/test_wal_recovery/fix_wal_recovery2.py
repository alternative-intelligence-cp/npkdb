with open('main.npk', 'r') as f:
    content = f.read()

content = content.replace('wal_close(fd)', 'wal_close(fd, 0i64)')

with open('main.npk', 'w') as f:
    f.write(content)
