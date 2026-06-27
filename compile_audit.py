import os
import glob
import subprocess

out_file = "/home/randy/Workspace/META/NPKDB/audits/a21/compilation.md"
os.makedirs(os.path.dirname(out_file), exist_ok=True)

with open(out_file, "w") as out:
    for root, _, files in os.walk("src"):
        for f in sorted(files):
            if f.endswith(".npk"):
                path = os.path.join(root, f)
                out.write(f"\n# File: {path}\n```nitpick\n")
                with open(path, "r") as src:
                    out.write(src.read())
                out.write("\n```\n")
    
    out.write("\n# Build Output\n```\n")
    result = subprocess.run(["python3", "flatten.py", "src/main.npk"], capture_output=True, text=True)
    out.write("flatten.py src/main.npk:\n")
    out.write(result.stdout)
    out.write(result.stderr)
    
    result = subprocess.run(["/home/randy/Workspace/REPOS/nitpick/build/nitpickc", "build/flattened.npk", "-o", "npkdb_bin", "--verify-level=0"], capture_output=True, text=True)
    out.write("\nnitpickc build/flattened.npk:\n")
    out.write(result.stdout)
    out.write(result.stderr)
    out.write("\n```\n")

print("Created", out_file)
