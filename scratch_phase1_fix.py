import os
import re

dirs_to_search = ["src", "tests"]
for d in dirs_to_search:
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith(".npk"):
                path = os.path.join(root, f)
                with open(path, "r") as src:
                    content = src.read()
                
                new_content = content
                # Fix )) from drop replacement
                new_content = re.sub(r'_?sys\((.*?)\)\);', r'_?sys(\1);', new_content)
                new_content = re.sub(r'_?npk_core_alloc\((.*?)\)\);', r'_?npk_core_alloc(\1);', new_content)
                new_content = re.sub(r'_?page_alloc\((.*?)\)\);', r'_?page_alloc(\1);', new_content)
                new_content = re.sub(r'_?json_arena_alloc\((.*?)\)\);', r'_?json_arena_alloc(\1);', new_content)

                # Wait, what if there's no semicolon immediately after? Like `_?sys(...))`
                new_content = re.sub(r'(_\?(?:sys|npk_core_alloc|page_alloc|json_arena_alloc)\([^)]*\))\)', r'\1', new_content)

                # Fix ->> to -> >
                new_content = new_content.replace('->>', '-> >')
                new_content = new_content.replace('> >', '> >') # wait
                new_content = re.sub(r'<(.*?)>>', r'<\1> >', new_content)

                # Find <?->>
                new_content = new_content.replace('cast_unchecked<?-> >', 'cast_unchecked<ThreadWorker-> >') # if it was that
                new_content = new_content.replace('cast_unchecked<?->>', 'cast_unchecked<ThreadWorker-> >') 

                if new_content != content:
                    with open(path, "w") as out:
                        out.write(new_content)
                    print(f"Fixed bugs in {path}")
