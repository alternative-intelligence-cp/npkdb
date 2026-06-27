with open('main.npk', 'r') as f:
    content = f.read()

content = content.replace('wal_close(wal_fd)', 'wal_close(wal_fd, 0i64)')
content = content.replace('wal_close(wal_fd1)', 'wal_close(wal_fd1, 0i64)')
content = content.replace('wal_close(wal_fd2)', 'wal_close(wal_fd2, 0i64)')
content = content.replace('wal_close(wal_fd3)', 'wal_close(wal_fd3, 0i64)')
content = content.replace('wal_close(wal_fd4)', 'wal_close(wal_fd4, 0i64)')

with open('main.npk', 'w') as f:
    f.write(content)
