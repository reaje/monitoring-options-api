import asyncio
from uuid import UUID
from typing import Optional
from pathlib import Path
import sys
# Ensure imports resolve when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.database.repositories.accounts import AccountsRepository
from app.database.repositories.options import OptionsRepository
from app.services.roll_calculator import roll_calculator


async def main(position_id: Optional[str] = None):
    if position_id:
        pos = await OptionsRepository.get_by_id(UUID(position_id))
        if not pos:
            print(f"Position not found: {position_id}")
            return
        user_id = None
        # Fetch account to get user_id
        acct = await AccountsRepository.get_by_id(UUID(pos["account_id"]))
        user_id = UUID(acct["user_id"]) if acct and acct.get("user_id") else None
        preview = await roll_calculator.get_roll_preview(UUID(position_id), auth_user_id=user_id)
        print({
            "position_id": position_id,
            "suggestions": preview.get("suggestions", []),
            "suggestions_count": len(preview.get("suggestions", [])),
            "current": preview.get("current_position", {}),
        })
        return

    # No position provided: pick first user/account and first OPEN position
    accounts = await AccountsRepository.get_all()
    if not accounts:
        print("No accounts found")
        return
    # Prefer first account
    acct = accounts[0]
    user_id = UUID(acct["user_id"]) if acct.get("user_id") else None
    positions = await OptionsRepository.get_open_positions(UUID(acct["id"]), auth_user_id=user_id)
    if not positions:
        print(f"No OPEN positions for account {acct['id']}")
        return
    pos = positions[0]
    preview = await roll_calculator.get_roll_preview(UUID(pos["id"]), auth_user_id=user_id)
    print({
        "position_id": pos["id"],
        "ticker": pos.get("ticker"),
        "strike": pos.get("strike"),
        "expiration": pos.get("expiration"),
        "suggestions_count": len(preview.get("suggestions", [])),
        "first_suggestion": (preview.get("suggestions", []) or [None])[0],
    })


if __name__ == "__main__":
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(arg))

