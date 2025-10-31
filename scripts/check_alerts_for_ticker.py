import argparse
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List
from pathlib import Path

# Ensure 'app' imports resolve when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.supabase_client import supabase
from app.config import settings


def _is_today(iso_str: str) -> bool:
    try:
        # Expecting e.g. '2025-10-27T11:00:31.858702Z' or without 'Z'
        if iso_str.endswith("Z"):
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(iso_str)
        now = datetime.now(timezone.utc)
        return dt.astimezone(timezone.utc).date() == now.date()
    except Exception:
        return False


def fetch_alerts_for_ticker(ticker: str, today_only: bool = True) -> List[Dict[str, Any]]:
    # Prefer explicit schema if available on client
    try:
        # Newer supabase-py exposes postgrest with schema selection
        query = supabase.postgrest.schema(settings.DB_SCHEMA).table("alert_queue")
    except Exception:
        # Fallback to default .table(); our client wrapper tries to set schema_name
        query = supabase.table("alert_queue")

    res = query.select("id,account_id,option_position_id,reason,payload,status,created_at").order(
        "created_at"
    ).execute()
    data = res.data or []

    filtered: List[Dict[str, Any]] = []
    for row in data:
        payload = row.get("payload") or {}
        # payload might come as JSON string depending on driver
        if isinstance(payload, str):
            try:
                import json as _json

                payload = _json.loads(payload)
            except Exception:
                payload = {}
        if str(payload.get("ticker", "")).upper() == ticker.upper():
            if today_only:
                created_at = row.get("created_at") or ""
                if _is_today(created_at):
                    filtered.append(row)
            else:
                filtered.append(row)
    return filtered


def main():
    parser = argparse.ArgumentParser(description="Check alert_queue for a specific ticker")
    parser.add_argument("--ticker", required=False, default="VALE3")
    parser.add_argument("--all", action="store_true", help="Do not restrict to today's alerts")
    args = parser.parse_args()

    ticker = args.ticker
    today_only = not args.all

    alerts = fetch_alerts_for_ticker(ticker, today_only=today_only)

    print({
        "ticker": ticker,
        "today_only": today_only,
        "count": len(alerts),
    })
    for a in alerts:
        payload = a.get("payload") or {}
        if isinstance(payload, str):
            try:
                import json as _json

                payload = _json.loads(payload)
            except Exception:
                payload = {}
        print(
            {
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
            }
        )


if __name__ == "__main__":
    sys.exit(main())

