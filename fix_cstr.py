import sys
files = [
    "src/storage/compaction.npk",
    "src/storage/flush.npk",
    "src/storage/sstable.npk",
    "src/storage/wal.npk",
    "src/engine/catalog.npk",
    "src/util/bloom.npk",
    "src/util/config.npk",
    "src/document/json_parser.npk",
    "src/network/controllers.npk"
]

for f in files:
    with open(f, "r") as fp:
        lines = fp.readlines()
    
    with open(f, "w") as fp:
        for line in lines:
            fp.write(line)
            if "string_to_cstr(" in line:
                # Find the variable name
                # e.g. int64:c_path = string_to_cstr(path);
                if "int64:" in line and "=" in line:
                    var_name = line.split("int64:")[1].split("=")[0].strip()
                    indent = line[:len(line) - len(line.lstrip())]
                    if var_name == "key_cstr" and f.endswith("controllers.npk"):
                        fp.write(indent + "drop(npk_core_dalloc(" + var_name + "));\n")
                    else:
                        fp.write(indent + "defer { _?npk_core_dalloc(" + var_name + "); }\n")
