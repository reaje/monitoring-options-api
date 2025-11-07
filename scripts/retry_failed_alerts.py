"""Retry FAILED alerts by setting them back to PENDING.

Usage:
  python backend/scripts/retry_failed_alerts.py [hours] [limit]

Defaults: hours=24, limit=100
"""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Optional

# Ensure repository root/backend on path
CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from uuid import UUID
from app.database.repositories.alerts import AlertQueueRepository


async def main(hours: int = 24, limit: int = 100):
    failed = await AlertQueueRepository.get_failed_alerts(hours=hours, limit=limit)
    print(f"FAILED found: {len(failed)} (last {hours}h, limit {limit})")
    retried = 0
    for a in failed:
        try:
            await AlertQueueRepository.retry_failed_alert(UUID(a["id"]))
            retried += 1
        except Exception as e:
            print(f"Failed to retry {a.get('id')}: {e}")
    print(f"Retried: {retried}")


if __name__ == "__main__":
    h = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    asyncio.run(main(h, lim))

