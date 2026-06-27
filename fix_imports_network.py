import sys

def process(file_path):
    with open(file_path, "r") as f:
        content = f.read()
    
    content = content.replace('use "channel.npk".*;\n', 'use "../../../nitpick-packages/packages/nitpick-channel/src/nitpick_channel.npk".*;\n')
    content = content.replace('use "thread.npk".*;\n', 'use "../../../nitpick-packages/packages/nitpick-thread/src/nitpick_thread.npk".*;\n')
    content = content.replace('use "string_convert.npk".*;\n', 'use "../../../nitpick-packages/packages/nitpick-string-convert/src/string_convert.npk".*;\n')
    
    with open(file_path, "w") as f:
        f.write(content)

process("src/network/server.npk")
process("src/network/http_worker.npk")
