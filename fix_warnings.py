import os
import re

log = open("tests/all.log").read()
errs = log.split('\n')
current_file = None

for i, line in enumerate(errs):
    # test_compaction_correctness.npk:0:0: warning: ...
    # :27:5: warning: [unused-parameter] parameter 'err' ...
    m = re.match(r'^([a-zA-Z0-9_\./]+):0:0: warning:', line)
    if m:
        current_file = m.group(1)
        if current_file.endswith(".npk") and not current_file.startswith("/"):
            # find the full path
            for root, dirs, files in os.walk("tests"):
                if current_file in files:
                    current_file = os.path.join(root, current_file)
                    break
        continue
    
    m2 = re.match(r'^(/home/randy[a-zA-Z0-9_\./]+):0:0: warning:', line)
    if m2:
        current_file = m2.group(1)
        continue

    m = re.match(r'^:(\d+):\d+: warning: \[unused-parameter\] parameter \'(.*?)\'', line)
    if not m:
        m = re.match(r'^:(\d+):\d+: warning: \[unused-variable\] variable \'(.*?)\'', line)
    
    if m and current_file:
        line_no = int(m.group(1)) - 1
        var = m.group(2)
        content = open(current_file).read().split('\n')
        # Insert drop(var); right after the line if it's a variable declaration, or inside the function if parameter
        # A simpler approach: just insert it at the end of the line
        # but what if it's a parameter? insert it at line_no + 1
        content[line_no] = content[line_no] + f" drop({var});"
        open(current_file, 'w').write('\n'.join(content))
        
print("Done fixing warnings")
