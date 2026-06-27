import os

src_dir = '/home/randy/Workspace/REPOS/npkdb/src'
out_file = '/home/randy/Workspace/META/NPKDB/audits/a23/compilation.md'
os.makedirs(os.path.dirname(out_file), exist_ok=True)

with open(out_file, 'w') as f:
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.npk') or file.endswith('.h') or file.endswith('.c'):
                filepath = os.path.join(root, file)
                relpath = os.path.relpath(filepath, '/home/randy/Workspace/REPOS/npkdb')
                f.write(f'# {relpath}\n\n')
                f.write('```nitpick\n')
                with open(filepath, 'r') as sf:
                    f.write(sf.read())
                f.write('\n```\n\n')

    f.write('# Build Output\n\n')
    f.write('```\n')
    with open('/home/randy/Workspace/REPOS/npkdb/tests/all_new.log', 'r') as logf:
        for line in logf:
            if '[DEBUG' not in line:
                f.write(line)
    f.write('```\n')
print("Done")
