with open("tests/test_distance/main.npk", "r") as f:
    lines = f.readlines()

test_count = 1
for i, line in enumerate(lines):
    if "drop(assert_" in line or "if (" in line and "exit" in line:
        if test_count == 49:
            print(f"Line {i+1}: {line.strip()}")
            # Print previous 10 lines context
            for j in range(max(0, i-10), i+2):
                print(f"{j+1}: {lines[j].strip()}")
            break
        test_count += 1
