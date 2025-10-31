import argparse
import asyncio
from pathlib import Path
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

# Ensure 'app' imports resolve when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.repositories.accounts import AccountsRepository
from app.database.repositories.alerts import AlertQueueRepository


def _is_today_prefix(created_at: str) -> bool:
    if not created_at:
        return False
    try:
        # Robust: compare only the YYYY-MM-DD prefix
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return str(created_at).startswith(today)
    except Exception:
        return False


async def delete_todays_alerts_for_ticker(ticker: str) -> Dict[str, Any]:
    accounts = await AccountsRepository.get_all()
    total_examined = 0
    total_matched = 0
    total_deleted = 0
    deleted_ids: List[str] = []

    for acc in accounts:
        account_id = acc.get("id")
        user_id = acc.get("user_id")
        if not account_id or not user_id:
            continue
        alerts = await AlertQueueRepository.get_by_account_id(
            account_id=account_id,
            status=None,
            auth_user_id=user_id,
        )
        for a in alerts:
            total_examined += 1
            payload = a.get("payload") or {}
            if isinstance(payload, str):
                try:
                    import json as _json
                    payload = _json.loads(payload)
                except Exception:
                    payload = {}
            if str(payload.get("ticker", "")).upper() != ticker.upper():
                continue
            if a.get("reason") != "roll_trigger":
                continue
            if not _is_today_prefix(a.get("created_at") or ""):
                continue
            total_matched += 1
            ok = await AlertQueueRepository.delete(a.get("id"), auth_user_id=user_id)
            if ok:
                total_deleted += 1
                deleted_ids.append(str(a.get("id")))

    return {
        "ticker": ticker,
        "examined": total_examined,
        "matched_today": total_matched,
        "deleted": total_deleted,
        "deleted_ids": deleted_ids,
    }


async def amain() -> int:
    parser = argparse.ArgumentParser(description="Delete today's roll_trigger alerts for a ticker (RLS-aware)")
    parser.add_argument("--ticker", required=False, default="VALE3")
    args = parser.parse_args()

    result = await delete_todays_alerts_for_ticker(args.ticker)
    try:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception:
        print(result)
    return 0


def main() -> int:
    return asyncio.run(amain())


if __name__ == "__main__":
    raise SystemExit(main())

