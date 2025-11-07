"""Patch all PENDING alerts to include a phone number in payload.

Usage:
  python backend/scripts/patch_alerts_phone.py <phone_digits> [limit]

Example:
  python backend/scripts/patch_alerts_phone.py 5571991776091 200
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


async def main(phone: str, limit: int = 100):
    # Normalize: keep only digits
    digits = ''.join(ch for ch in phone if ch.isdigit())
    pending = await AlertQueueRepository.get_pending_alerts(limit)
    print(f"Pending: {len(pending)} | Patching phone: {digits}")
    patched = 0
    for a in pending:
        try:
            await AlertQueueRepository.merge_payload(UUID(a['id']), {"phone": digits})
            patched += 1
        except Exception as e:
            print(f"Failed to patch {a.get('id')}: {e}")
    print(f"Patched: {patched}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: patch_alerts_phone.py <phone_digits> [limit]")
        sys.exit(1)
    phone = sys.argv[1]
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    asyncio.run(main(phone, lim))

