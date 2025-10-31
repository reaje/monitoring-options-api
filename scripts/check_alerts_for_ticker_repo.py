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


def _is_today(iso_str: str) -> bool:
    try:
        if not iso_str:
            return False
        # Robust: compare only the YYYY-MM-DD prefix to avoid timezone suffix quirks
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return str(iso_str).startswith(today)
    except Exception:
        return False


async def fetch_alerts_for_ticker_repo(ticker: str, today_only: bool = True) -> List[Dict[str, Any]]:
    accounts = await AccountsRepository.get_all()
    results: List[Dict[str, Any]] = []
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
            payload = a.get("payload") or {}
            if isinstance(payload, str):
                try:
                    import json as _json
                    payload = _json.loads(payload)
                except Exception:
                    payload = {}
            if str(payload.get("ticker", "")).upper() != ticker.upper():
                continue
            if today_only and not _is_today(a.get("created_at") or ""):
                continue
            results.append({
                "account_id": account_id,
                "user_id": user_id,
                "id": a.get("id"),
                "created_at": a.get("created_at"),
                "reason": a.get("reason"),
                "status": a.get("status"),
                "option_position_id": a.get("option_position_id"),
                "payload": {
                    "rule_id": payload.get("rule_id"),
                    "dte": payload.get("dte"),
                    "premium": payload.get("premium"),
                    "price": payload.get("price"),
                    "strike": payload.get("strike"),
                    "expiration": payload.get("expiration"),
                },
            })
    return results


async def amain() -> int:
    parser = argparse.ArgumentParser(description="Check alert_queue for a ticker using repositories (RLS-aware)")
    parser.add_argument("--ticker", required=False, default="VALE3")
    parser.add_argument("--all", action="store_true", help="Do not restrict to today's alerts")
    args = parser.parse_args()

    alerts = await fetch_alerts_for_ticker_repo(args.ticker, today_only=(not args.all))

    out = {
        "ticker": args.ticker,
        "today_only": not args.all,
        "count": len(alerts),
        "alerts": alerts,
    }
    try:
        import json
        print(json.dumps(out, ensure_ascii=False, indent=2)[:4000])
    except Exception:
        print(out)
    return 0


def main() -> int:
    return asyncio.run(amain())


if __name__ == "__main__":
    raise SystemExit(main())

