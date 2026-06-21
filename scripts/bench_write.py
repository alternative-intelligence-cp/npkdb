import time
import requests
import json
import sys

URL = "http://127.0.0.1:8080/collections/default/docs"
TOTAL_VECTORS = 10000
BATCH_SIZE = 1000

def main():
    print(f"Starting write benchmark: {TOTAL_VECTORS} vectors in batches of {BATCH_SIZE}")
    
    start_time = time.time()
    
    for i in range(0, TOTAL_VECTORS, BATCH_SIZE):
        batch = []
        for j in range(BATCH_SIZE):
            vector_id = i + j
            batch.append({
                "id": f"vec_{vector_id}",
                "vector": [0.1] * 1536,
                "metadata": {"index": vector_id}
            })
            
        # Send batch
        response = requests.put(URL, json={"docs": batch})
        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            print(f"Request Headers: {response.request.headers}")
            sys.exit(1)
            
        if (i + BATCH_SIZE) % 100_000 == 0:
            print(f"Ingested {i + BATCH_SIZE} vectors...")
            
    end_time = time.time()
    total_time = end_time - start_time
    ops_sec = TOTAL_VECTORS / total_time
    
    print(f"\n--- WRITE BENCHMARK RESULTS ---")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Ops/sec:    {ops_sec:.2f}")

if __name__ == "__main__":
    main()
