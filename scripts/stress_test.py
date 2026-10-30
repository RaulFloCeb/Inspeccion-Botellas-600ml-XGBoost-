"""Envía solicitudes concurrentes a /predict y resume la latencia.

Uso: python scripts/stress_test.py [url_base] [solicitudes] [concurrencia]
Solo usa la librería estándar.
"""
import json
import statistics
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
TOTAL = int(sys.argv[2]) if len(sys.argv) > 2 else 100
WORKERS = int(sys.argv[3]) if len(sys.argv) > 3 else 100
BODY = json.dumps({"fill_level_ml": 598.5, "label_present_num": 1}).encode()


def call(_):
    request = urllib.request.Request(
        f"{BASE_URL}/predict", data=BODY, headers={"Content-Type": "application/json"}
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            json.load(response)
            status = response.status
    except Exception as exc:
        return None, repr(exc)
    return (time.perf_counter() - start) * 1000, status


started = time.perf_counter()
with ThreadPoolExecutor(max_workers=WORKERS) as pool:
    results = list(pool.map(call, range(TOTAL)))
wall = time.perf_counter() - started

latencies = sorted(ms for ms, status in results if status == 200)
errors = [status for ms, status in results if status != 200]
print(f"Solicitudes: {TOTAL}  Concurrencia: {WORKERS}  OK: {len(latencies)}  Errores: {len(errors)}")
if errors:
    print("Primer error:", errors[0])
if latencies:
    p99 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.99))]
    print(
        f"Latencia ms  media: {statistics.mean(latencies):.1f}  mediana: {statistics.median(latencies):.1f}"
        f"  p99: {p99:.1f}  max: {latencies[-1]:.1f}"
    )
    print(f"Tiempo total: {wall:.2f} s  Rendimiento: {TOTAL / wall:.0f} sol/s")
