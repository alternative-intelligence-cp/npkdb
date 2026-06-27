import os
import glob

output_file = "/home/randy/Workspace/META/NPKDB/audits/a24/compilation.md"

with open(output_file, "w") as out:
    out.write("# NPKDB Source Compilation\n\n")
    for filepath in glob.glob("src/**/*.npk", recursive=True):
        out.write(f"## File: `{filepath}`\n\n")
        out.write("```nitpick\n")
        with open(filepath, "r") as f:
            out.write(f.read())
        out.write("\n```\n\n")
