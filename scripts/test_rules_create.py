import asyncio
from uuid import uuid4, UUID
from pathlib import Path
import sys

# Ensure backend package on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.repositories.rules import RulesRepository

async def main():
    # Fake user/account UUIDs just to trigger code paths
    user_id = UUID('00000000-0000-0000-0000-000000000001')
    account_id = uuid4()
    try:
        data = {
            "account_id": str(account_id),
            "delta_threshold": 0.6,
            "dte_min": 3,
            "dte_max": 5,
            "spread_threshold": 5.0,
            "price_to_strike_ratio": 0.98,
            "min_volume": 1000,
            "max_spread": 0.05,
            "min_oi": 5000,
            "target_otm_pct_low": 0.03,
            "target_otm_pct_high": 0.08,
            "notify_channels": ["whatsapp", "sms"],
            "is_active": True,
        }
        rule = await RulesRepository.create(data, auth_user_id=user_id)
        print("CREATED:", rule)
    except Exception as e:
        print("ERR:", type(e).__name__, e)

if __name__ == '__main__':
    asyncio.run(main())

