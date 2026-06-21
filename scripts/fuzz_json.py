#!/usr/bin/env python3
import sys
import random
import string
import json
import subprocess

def generate_payload():
    choice = random.randint(0, 6)
    if choice == 0:
        return json.dumps({"test": "valid", "val": random.randint(1, 1000)})
    elif choice == 1:
        return '{"test": "\xff\xfe\xfd"}'
    elif choice == 2:
        return "[" * 128 + "]" * 128
    elif choice == 3:
        return '{"large": 999999999999999999999999999999}'
    elif choice == 4:
        return '{"truncated": '
    elif choice == 5:
        return ''.join(random.choices(string.printable, k=100))
    elif choice == 6:
        return '{"test": \0}'

def main():
    iterations = 10000
    for i in range(iterations):
        payload = generate_payload()
        with open("fuzz_payload.json", "w") as f:
            f.write(payload)
        
        result = subprocess.run(["./build/fuzz_json_bin"], capture_output=True)
        # If the process segfaults or aborts, it exits with a negative returncode or a high value like 134/139
        if result.returncode < 0 or result.returncode > 128:
            print(f"CRASH detected on iteration {i}!")
            print(f"Payload: {payload}")
            print(f"Exit code: {result.returncode}")
            print(f"Output: {result.stdout.decode('utf-8', errors='ignore')}")
            sys.exit(1)
            
    print("Fuzzing completed successfully!")

if __name__ == "__main__":
    main()
