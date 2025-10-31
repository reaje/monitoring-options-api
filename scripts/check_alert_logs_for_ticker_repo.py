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
from app.database.repositories.alert_logs import AlertLogsRepository


def _is_today_prefix(created_at: str) -> bool:
    if not created_at:
        return False
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return str(created_at).startswith(today)
    except Exception:
        return False


async def fetch_alerts_with_logs_for_ticker(ticker: str, today_only: bool = True) -> Dict[str, Any]:
    accounts = await AccountsRepository.get_all()
    out_alerts: List[Dict[str, Any]] = []
    total_logs = 0

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
            if today_only and not _is_today_prefix(a.get("created_at") or ""):
                continue

            # Fetch logs for this alert id
            logs = await AlertLogsRepository.get_by_queue_id(
                a.get("id"), auth_user_id=user_id
            )
            total_logs += len(logs)

            out_alerts.append({
                "account_id": account_id,
                "user_id": user_id,
                "id": a.get("id"),
                "created_at": a.get("created_at"),
                "reason": a.get("reason"),
                "status": a.get("status"),
                "payload": {
                    "rule_id": payload.get("rule_id"),
                    "dte": payload.get("dte"),
                    "premium": payload.get("premium"),
                    "price": payload.get("price"),
                    "strike": payload.get("strike"),
                    "expiration": payload.get("expiration"),
                },
                "logs": logs,
            })

    return {
        "ticker": ticker,
        "today_only": today_only,
        "alerts_count": len(out_alerts),
        "total_logs": total_logs,
        "alerts": out_alerts,
    }


async def amain() -> int:
    parser = argparse.ArgumentParser(description="Check alert logs (deliveries) for alerts of a ticker using repositories (RLS-aware)")
    parser.add_argument("--ticker", required=False, default="VALE3")
    parser.add_argument("--all", action="store_true", help="Include alerts from any day (not only today)")
    args = parser.parse_args()

    result = await fetch_alerts_with_logs_for_ticker(args.ticker, today_only=(not args.all))
    try:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2)[:8000])
    except Exception:
        print(result)
    return 0


def main() -> int:
    return asyncio.run(amain())


if __name__ == "__main__":
    raise SystemExit(main())

