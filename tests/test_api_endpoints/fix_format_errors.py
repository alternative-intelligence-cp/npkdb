import os

def fix_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    new_content = content.replace("format_error_status", "raw format_error_status")
    new_content = new_content.replace("format_error_json", "raw format_error_json")
    
    # Fix double "raw raw" if it happens
    new_content = new_content.replace("raw raw format", "raw format")

    if new_content != content:
        with open(filepath, "w") as f:
            f.write(new_content)
        print(f"Fixed {filepath}")

fix_file("../../src/network/controllers.npk")
fix_file("controllers_mock.npk")
