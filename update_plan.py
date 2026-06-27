import re

path = "/home/randy/Workspace/META/NPKDB/ROADMAP/current/0.22/RELEASE_0.22.0.md"
with open(path, "r") as f:
    content = f.read()

content = content.replace("[ ]", "[x]")
content = content.replace("⬜ NOT STARTED", "✅ DONE")

with open(path, "w") as f:
    f.write(content)
