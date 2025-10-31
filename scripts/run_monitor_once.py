"""Run monitor worker once (manual trigger).

Usage:
  python backend/scripts/run_monitor_once.py
"""
from __future__ import annotations

import asyncio
from pathlib import Path
import sys

# Ensure imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.workers.monitor_worker import monitor_worker  # noqa: E402


if __name__ == "__main__":
    out = asyncio.run(monitor_worker.run())
    # Print a compact summary if available
    try:
        from json import dumps
        print(dumps(out)[:2000])
    except Exception:
        print(str(out))

