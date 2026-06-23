import os
import glob

for f in glob.glob('src/**/*.npk', recursive=True):
    with open(f, 'r') as file:
        content = file.read()
    new_content = content.replace('raw npk_mem_read_string', 'npk_mem_read_string')
    new_content = new_content.replace('raw npk_mem_write_string', 'npk_mem_write_string')
    if new_content != content:
        with open(f, 'w') as file:
            file.write(new_content)
