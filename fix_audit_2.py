import re
import os

with open("/home/randy/Workspace/META/NPKDB/audits/a21/audit.md", "r") as f:
    audit = f.read()

# Extract block for Directive 1
d1_start = audit.find("pub func:controller\_insert")
d1_end = audit.find("};", audit.find("pub func:controller\_search")) + 2
if d1_start != -1 and d1_end != -1:
    d1_code = audit[d1_start:d1_end]
    d1_code = d1_code.replace("\\", "")
    with open("src/network/controllers.npk", "r") as f:
        controllers = f.read()
    # Replace the existing code
    c_start = controllers.find("pub func:controller_insert")
    c_end = controllers.find("};", controllers.find("pub func:controller_search")) + 2
    if c_start != -1 and c_end != -1:
        controllers = controllers[:c_start] + d1_code + controllers[c_end:]
        with open("src/network/controllers.npk", "w") as f:
            f.write(controllers)
        print("Directive 1 applied.")
    else:
        print("Could not find functions in controllers.npk")
else:
    print("Could not find Directive 1 code in audit.md")

# Extract block for Directive 2
d2_start = audit.find("pub func:evaluate\_filter")
d2_end = audit.find("};", d2_start) + 2
if d2_start != -1 and d2_end != -1:
    d2_code = audit[d2_start:d2_end]
    d2_code = d2_code.replace("\\", "")
    with open("src/query/evaluator.npk", "r") as f:
        evaluator = f.read()
    c_start = evaluator.find("pub func:evaluate_filter")
    c_end = evaluator.find("};", c_start) + 2
    if c_start != -1 and c_end != -1:
        evaluator = evaluator[:c_start] + d2_code + evaluator[c_end:]
        with open("src/query/evaluator.npk", "w") as f:
            f.write(evaluator)
        print("Directive 2 applied.")
    else:
        print("Could not find evaluate_filter in evaluator.npk")

# Fix http_worker.npk thread signature
with open("src/network/http_worker.npk", "r") as f:
    http_worker = f.read()
if "wild ?->:worker_fn" in http_worker:
    http_worker = http_worker.replace("wild ?->:worker_fn", "wild any->:worker_fn")
    with open("src/network/http_worker.npk", "w") as f:
        f.write(http_worker)
    print("Updated http_worker_start in http_worker.npk")

