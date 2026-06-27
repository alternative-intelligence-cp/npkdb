crc_table = []
for i in range(256):
    c = i
    for j in range(8):
        if c & 1:
            c = 0xEDB88320 ^ (c >> 1)
        else:
            c = c >> 1
    crc_table.append(c)

crc = 0xFFFFFFFF
# 9 length header (8 bytes usually or 4 bytes?)
# Let's see what npk_mem_write_string does. Usually it's just raw bytes? No, npk_mem_write_string usually is implemented as string_to_cstr?
# Actually npk_mem_write_string is not a standard function. Let me grep for it.
