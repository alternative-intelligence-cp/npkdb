import os

output_file = "/home/randy/Workspace/META/NPKDB/audits/a22/compilation.md"
src_dir = "/home/randy/Workspace/REPOS/npkdb/src"
build_output_file = "/home/randy/Workspace/REPOS/npkdb/build_output.txt"

with open(output_file, "w") as out:
    out.write("# NPKDB Source Code Compilation\n\n")
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".npk"):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, src_dir)
                out.write(f"\n\n--- {rel_path} ---\n\n")
                with open(file_path, "r") as f:
                    out.write(f.read())
                    
    out.write("\n\n## build output\n\n```\n")
    if os.path.exists(build_output_file):
        with open(build_output_file, "r") as f:
            out.write(f.read())
    out.write("\n```\n")
