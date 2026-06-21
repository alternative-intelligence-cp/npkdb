import urllib.request
import json
import threading

def worker(start, end):
    for i in range(start, end):
        req = urllib.request.Request(
            'http://127.0.0.1:8080/collections/crash_test/docs',
            data=json.dumps({"id": i, "padding": "X"*50}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='PUT'
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                response.read()
        except Exception as e:
            print(f"Error on {i}: {e}")

threads = []
chunk = 10000 // 20
for i in range(20):
    t = threading.Thread(target=worker, args=(i*chunk, (i+1)*chunk))
    t.start()
    threads.append(t)

for t in threads:
    t.join()

print("Completed 10,000 inserts.")
