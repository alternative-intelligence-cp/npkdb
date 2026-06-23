import os
import re

out_file = '/home/randy/.gemini/antigravity-ide/brain/0dfd17ae-e1cb-446d-99e7-351f4487e296/artifacts/compilation_5.md'
# Wait, artifacts directory is /home/randy/.gemini/antigravity-ide/brain/0dfd17ae-e1cb-446d-99e7-351f4487e296

out_file = '/home/randy/.gemini/antigravity-ide/brain/0dfd17ae-e1cb-446d-99e7-351f4487e296/compilation_5.md'

with open(out_file, 'w') as f:
    f.write('# NPKDB Source Code & Compiler Log Phase 5\n\n')
    
    # Write source code
    for root, dirs, files in os.walk('src'):
        for file in sorted(files):
            if file.endswith('.npk'):
                filepath = os.path.join(root, file)
                f.write(f'## `{filepath}`\n\n```nitpick\n')
                with open(filepath, 'r') as sf:
                    f.write(sf.read())
                f.write('\n```\n\n')
                
    f.write('# Final Compiler Log\n\n```\n')
    with open('real_errors.txt', 'r') as sf:
        log = sf.read()
        # strip ansi
        log = re.sub(r'\x1B\[[0-9;]*[mK]', '', log)
        f.write(log)
    f.write('\n```\n')
