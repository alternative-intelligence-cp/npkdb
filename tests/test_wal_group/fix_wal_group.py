import re

with open('main.npk', 'r') as f:
    content = f.read()

content = content.replace('drop(wal_enable_group_commit(wal_fd));', 'int64:wal_state = wal_enable_group_commit() ? 0i64;')
content = content.replace('drop(wal_enable_group_commit(wal_fd2));', 'int64:wal_state2 = wal_enable_group_commit() ? 0i64;')
content = content.replace('drop(wal_enable_group_commit(wal_fd3));', 'int64:wal_state3 = wal_enable_group_commit() ? 0i64;')
content = content.replace('drop(wal_enable_group_commit(wal_fd5));', 'int64:wal_state5 = wal_enable_group_commit() ? 0i64;')

content = content.replace('wal_batch_append_put(wal_fd,', 'wal_batch_append_put(wal_state, wal_fd,')
content = content.replace('wal_batch_append_put(wal_fd2,', 'wal_batch_append_put(wal_state2, wal_fd2,')
content = content.replace('wal_batch_append_put(wal_fd3,', 'wal_batch_append_put(wal_state3, wal_fd3,')
content = content.replace('wal_batch_append_put(wal_fd5,', 'wal_batch_append_put(wal_state5, wal_fd5,')

content = content.replace('wal_batch_append_delete(wal_fd5,', 'wal_batch_append_delete(wal_state5, wal_fd5,')

content = content.replace('wal_batch_should_flush(wal_fd)', 'wal_batch_should_flush(wal_fd, wal_state)')

content = content.replace('wal_batch_flush(wal_fd)', 'wal_batch_flush(wal_fd, wal_state)')
content = content.replace('wal_batch_flush(wal_fd2)', 'wal_batch_flush(wal_fd2, wal_state2)')
content = content.replace('wal_batch_flush(wal_fd3)', 'wal_batch_flush(wal_fd3, wal_state3)')
content = content.replace('wal_batch_flush(wal_fd5)', 'wal_batch_flush(wal_fd5, wal_state5)')

content = content.replace('wal_close(wal_fd)', 'wal_close(wal_fd, wal_state)')
content = content.replace('wal_close(wal_fd2)', 'wal_close(wal_fd2, wal_state2)')
content = content.replace('wal_close(wal_fd3)', 'wal_close(wal_fd3, wal_state3)')
content = content.replace('wal_close(wal_fd4)', 'wal_close(wal_fd4, 0i64)')
content = content.replace('wal_close(wal_fd5)', 'wal_close(wal_fd5, wal_state5)')


with open('main.npk', 'w') as f:
    f.write(content)
