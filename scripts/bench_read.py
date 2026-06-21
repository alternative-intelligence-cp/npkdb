import time
import requests
import json
import numpy as np
import random

URL = "http://127.0.0.1:8080/collections/default/search"
TOTAL_QUERIES = 10_000

def main():
    print(f"Starting read benchmark: {TOTAL_QUERIES} queries")
    
    latencies = []
    
    for i in range(TOTAL_QUERIES):
        query = {
            "vector": [random.random() for _ in range(1536)],
            "k": 10,
            "filter": {"$eq": {"index": random.randint(0, 1000000)}}
        }
        
        start = time.perf_counter()
        response = requests.post(URL, json=query)
        end = time.perf_counter()
        
        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            # continue rather than exit so we can see partial results
            continue
            
        latencies.append((end - start) * 1000) # in ms
        
        if (i + 1) % 1000 == 0:
            print(f"Executed {i + 1} queries...")
            
    if not latencies:
        print("No successful queries.")
        return
        
    latencies = np.array(latencies)
    
    print(f"\n--- READ BENCHMARK RESULTS ---")
    print(f"Total queries: {len(latencies)}")
    print(f"p50 Latency:   {np.percentile(latencies, 50):.2f} ms")
    print(f"p90 Latency:   {np.percentile(latencies, 90):.2f} ms")
    print(f"p95 Latency:   {np.percentile(latencies, 95):.2f} ms")
    print(f"p99 Latency:   {np.percentile(latencies, 99):.2f} ms")
    print(f"Avg Latency:   {np.mean(latencies):.2f} ms")

if __name__ == "__main__":
    main()
