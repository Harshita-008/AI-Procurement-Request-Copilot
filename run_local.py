"""One-command local start: mock vendor-risk API + Streamlit UI."""
from __future__ import annotations

import subprocess
import sys
import time

from src.config import ROOT, UI_PORT, VENDOR_RISK_BASE_URL
from src.mock_api_runner import ensure_mock_api, is_mock_api_up


def main() -> None:
    procs: list[subprocess.Popen] = []
    try:
        api_proc = ensure_mock_api()
        print(f"Vendor-risk API {'started' if api_proc else 'already running'} at {VENDOR_RISK_BASE_URL}")
        if api_proc:
            procs.append(api_proc)
        print(f"Starting UI on http://127.0.0.1:{UI_PORT} ...")
        procs.append(subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", UI_PORT], cwd=ROOT))
        while all(p.poll() is None for p in procs):
            time.sleep(1)
            if not is_mock_api_up():
                print("Vendor-risk API is no longer reachable; tool failures will be surfaced in the UI.")
    except KeyboardInterrupt:
        print("Stopping local services ...")
    finally:
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        for proc in procs:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
