"""Run all services locally without Docker.  Usage:  python scripts/run_local.py
Ctrl+C stops everything. Each service uses its own data/ folder (own database)."""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICES = {  # folder -> port
    "user-service": 8001, "room-service": 8002, "message-service": 8003,
    "notification-service": 8004, "activity-service": 8005, "gateway": 8000,
}

procs = []
try:
    for name, port in SERVICES.items():
        folder = os.path.join(ROOT, "services", name)
        env = dict(os.environ, DB_PATH=os.path.join(ROOT, "data", f"{name}.db"))
        procs.append((name, subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--port", str(port), "--log-level", "warning"],
            cwd=folder, env=env)))
        print(f"started {name:22s} http://localhost:{port}/docs" if name != "gateway" else f"started {name:22s} http://localhost:{port}")
    print("\nOpen http://localhost:8000  (Ctrl+C to stop)")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    for _, p in procs:
        p.terminate()
