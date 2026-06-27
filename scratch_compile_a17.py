import os
import subprocess

src_dir = '/home/randy/Workspace/REPOS/npkdb/src'
out_dir = '/home/randy/Workspace/META/NPKDB/audits/a17'
out_file = os.path.join(out_dir, 'compilation.md')

if not os.path.exists(out_dir):
    os.makedirs(out_dir)

with open(out_file, 'w') as out:
    out.write('# NPKDB Source Compilation (a17)\n\n')
    
    for root, dirs, files in os.walk(src_dir):
        files.sort()
        dirs.sort()
        
        for file in files:
            if file.endswith('.npk'):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, src_dir)
                
                out.write(f'## {rel_path}\n\n')
                out.write('```nitpick\n')
                with open(filepath, 'r') as f:
                    out.write(f.read())
                out.write('\n```\n\n')

    out.write('## Build Output\n\n')
    out.write('```\n')
    
    # Run the build
    cmd = 'export PATH="/home/randy/Workspace/REPOS/nitpick/build:$PATH" && python3 flatten.py && npkc build/flattened.npk -o build/npkdb_server 2>&1'
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd='/home/randy/Workspace/REPOS/npkdb')
    out.write(res.stdout)
    if res.stderr:
        out.write('\nSTDERR:\n' + res.stderr)
    out.write('\n```\n')

print("NPKDB Compilation a17 complete.")
