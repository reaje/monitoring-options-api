"""Patch FAILED alerts (last N hours) to include phone number in payload.

Usage:
  python backend/scripts/patch_failed_alerts_phone.py <phone_digits> [hours] [limit]

Defaults: hours=48, limit=200
"""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Optional

CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from uuid import UUID
from app.database.repositories.alerts import AlertQueueRepository


async def main(phone: str, hours: int = 48, limit: int = 200):
    digits = ''.join(ch for ch in phone if ch.isdigit())
    failed = await AlertQueueRepository.get_failed_alerts(hours=hours, limit=limit)
    print(f"FAILED found: {len(failed)} (last {hours}h)")
    patched = 0
    for a in failed:
        try:
            await AlertQueueRepository.merge_payload(UUID(a['id']), {"phone": digits})
            patched += 1
        except Exception as e:
            print(f"Failed to patch {a.get('id')}: {e}")
    print(f"Patched: {patched}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: patch_failed_alerts_phone.py <phone_digits> [hours] [limit]")
        sys.exit(1)
    phone = sys.argv[1]
    hours = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    asyncio.run(main(phone, hours, limit))

