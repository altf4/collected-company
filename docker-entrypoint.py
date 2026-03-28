"""Docker entrypoint: initialize database on first run, then start uvicorn."""

import os
import subprocess
import sys


def main():
    db_path = os.path.join("data", "collected_company.db")

    if not os.path.exists(db_path):
        print("First run: initializing database and stores...")
    else:
        print("Syncing stores...")
    subprocess.run([sys.executable, "scripts/init_sample_stores.py"], check=True)

    os.execvp("uvicorn", [
        "uvicorn",
        "collected_company.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
    ])


if __name__ == "__main__":
    main()
