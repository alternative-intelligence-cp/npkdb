import subprocess
import time
import os

print("Waiting for test_stress_bin to start...")
time.sleep(2)

try:
    pid = subprocess.check_output(["pidof", "test_stress_bin"]).decode().strip()
    print(f"Found test_stress_bin PID: {pid}")
    
    gdb_cmd = f"gdb -p {pid} -batch -ex 'thread apply all bt' -ex 'quit'"
    output = subprocess.check_output(gdb_cmd, shell=True).decode()
    print("GDB Output:")
    print(output)
except Exception as e:
    print(f"Error: {e}")
