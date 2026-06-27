import re
import os

# 1. Update sys.npk to add mem_primitives
sys_path = 'src/storage/sys.npk'
with open(sys_path, 'r') as f:
    sys_content = f.read()
if 'mem_primitives' not in sys_content:
    sys_content = sys_content.replace('use "../util/error_codes.npk".*;\n', 'use "../util/error_codes.npk".*;\nuse "../util/mem_primitives.npk".*;\n')
    with open(sys_path, 'w') as f:
        f.write(sys_content)

# 2. Update wal.npk
wal_path = 'src/storage/wal.npk'
with open(wal_path, 'r') as f:
    wal_content = f.read()

wal_content = wal_content.replace('sys(OPEN, c_path, 1089i64, 420i64)', 'sys_open(c_path, 1089i64, 420i64)')
wal_content = wal_content.replace('sys(CLOSE, wal_fd)', 'sys_close(wal_fd)')
wal_content = wal_content.replace('sys(FSYNC, wal_fd)', 'sys_fsync(wal_fd)')
wal_content = wal_content.replace('sys(WRITE, wal_fd, buf, total_len)', 'sys_write(wal_fd, buf, total_len)')
wal_content = wal_content.replace('sys(WRITE, wal_fd, buf_ptr, buf_len)', 'sys_write(wal_fd, buf_ptr, buf_len)')
wal_content = wal_content.replace('sys(CLOCK_GETTIME, 1i64, timespec)', 'sys_clock_gettime(1i64, timespec)')

with open(wal_path, 'w') as f:
    f.write(wal_content)

# 3. Update tests/test_wal/main.npk
test_wal_path = 'tests/test_wal/main.npk'
with open(test_wal_path, 'r') as f:
    test_wal = f.read()

test_wal = test_wal.replace('sys(UNLINK, path)', 'sys_unlink(path)')
test_wal = test_wal.replace('sys(OPEN, path, 0i64, 0i64)', 'sys_open(string_to_cstr(path), 0i64, 0i64)')
test_wal = test_wal.replace('sys(READ, r_fd, buf, 34i64)', 'sys_read(r_fd, buf, 34i64)')
test_wal = test_wal.replace('sys(CLOSE, r_fd)', 'sys_close(r_fd)')

if 'sys.npk' not in test_wal:
    test_wal = test_wal.replace('use "../../src/storage/wal.npk".*;\n', 'use "../../src/storage/wal.npk".*;\nuse "../../src/storage/sys.npk".*;\n')

with open(test_wal_path, 'w') as f:
    f.write(test_wal)

print("Patching complete.")
