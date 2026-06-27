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
buf = b"123456789"
for byte_val in buf:
    idx = (crc ^ byte_val) & 0xFF
    table_val = crc_table[idx]
    crc = table_val ^ (crc >> 8)

crc = crc ^ 0xFFFFFFFF
print(f"CRC: {crc} / {hex(crc)}")
