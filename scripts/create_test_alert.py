from __future__ import annotations
import asyncio, os, sys
from typing import Any, Dict
CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from uuid import UUID
from app.database.repositories.accounts import AccountsRepository
from app.database.repositories.alerts import AlertQueueRepository

async def main():
    accounts = await AccountsRepository.get_all()
    if not accounts:
        print('No accounts found')
        return
    acc = accounts[0]
    print('Using account:', acc['id'], acc.get('name'))
    payload = {
        "ticker": "BBAS3",
        "side": "CALL",
        "strike": 21.5,
        "expiration": "2025-11-14",
        "dte": 8,
        # intentionally missing: price, premium, moneyness, otm_pct, delta
        "channels": ["whatsapp", "sms"],
        "phone": "5571991776091",
    }
    data = {
        "account_id": UUID(acc['id']),
        "option_position_id": None,
        "reason": "roll_trigger",
        "payload": payload,
        "status": "PENDING",
    }
    created = await AlertQueueRepository.create(data)
    print('Created alert:', created['id'])

if __name__ == '__main__':
    asyncio.run(main())

