import sys
import time
from concurrent.futures import ThreadPoolExecutor
import requests

BASE = "http://localhost:5000"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
QUERY = "radiohead creep"


def login(i):
    r = requests.post(f"{BASE}/auth/login", json={"email": f"load{i}@test.com", "password": "Passw0rd!"})
    return r.json()["data"]["access_token"]


def search(token):
    h = {"Authorization": f"Bearer {token}"}
    start = time.monotonic()
    job = requests.post(f"{BASE}/search/", json={"search_input": QUERY}, headers=h).json()["data"]["job_id"]
    while requests.get(f"{BASE}/search/status/{job}", headers=h).json()["data"]["status"] not in ("SUCCESS", "FAILURE"):
        time.sleep(0.2)
    return time.monotonic() - start


tokens = [login(i) for i in range(N)]
with ThreadPoolExecutor(N) as pool:
    times = sorted(pool.map(search, tokens))

print(f"n={N} p50={times[N // 2]:.2f}s p95={times[int(N * 0.95) - 1]:.2f}s")

