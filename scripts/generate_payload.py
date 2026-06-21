import json
import os

PAYLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
FILE_NAME = "scripts/bulk_insert.json"

def main():
    print(f"Generating {FILE_NAME} ({PAYLOAD_SIZE} bytes)...")
    
    # We want the total JSON file to be roughly 50MB.
    # The JSON structure is {"id": "bulk", "data": "X" * N}
    base_json = '{"id":"bulk","data":""}'
    padding_size = PAYLOAD_SIZE - len(base_json)
    
    payload = {
        "id": "bulk",
        "data": "X" * padding_size
    }
    
    with open(FILE_NAME, "w") as f:
        json.dump(payload, f)
        
    actual_size = os.path.getsize(FILE_NAME)
    print(f"Created {FILE_NAME} (Size: {actual_size} bytes)")

if __name__ == "__main__":
    main()
