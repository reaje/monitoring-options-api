"""Directly update premium_close_threshold for near-expiration rule (3-10 DTE)
for the BTG Pactual Investimentos account.

Usage:
  python backend/scripts/sql_update_premium_threshold.py
"""
from __future__ import annotations

import asyncio
import asyncpg
from pathlib import Path
import sys

# Ensure app config can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import settings  # noqa: E402

ACCOUNT_NAME = "BTG Pactual Investimentos"
TARGET_PREMIUM = 0.05  # R$ 0,05
NEAR_DTE_MIN, NEAR_DTE_MAX = 3, 10


async def main() -> int:
    # Use full DATABASE_URL to ensure SSL/search_path settings are applied consistently
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        # Find account id
        acc = await conn.fetchrow(
            f"SELECT id, name FROM {settings.DB_SCHEMA}.accounts WHERE lower(name)=lower($1) LIMIT 1",
            ACCOUNT_NAME,
        )
        if not acc:
            print({"error": f"Account not found: {ACCOUNT_NAME}"})
            return 1
        account_id = acc["id"]
        print({"account_id": str(account_id), "account_name": acc["name"]})

        # Update rule
        rows = await conn.fetch(
            f"""
            UPDATE {settings.DB_SCHEMA}.roll_rules rr
               SET premium_close_threshold = $1
             FROM {settings.DB_SCHEMA}.accounts a
            WHERE rr.account_id = a.id
              AND a.id = $2
              AND rr.dte_min = $3
              AND rr.dte_max = $4
         RETURNING rr.id, rr.dte_min, rr.dte_max, rr.premium_close_threshold
            """,
            TARGET_PREMIUM,
            account_id,
            NEAR_DTE_MIN,
            NEAR_DTE_MAX,
        )
        out = [{"id": str(r["id"]), "dte": [r["dte_min"], r["dte_max"]], "premium_close_threshold": float(r["premium_close_threshold"]) if r["premium_close_threshold"] is not None else None} for r in rows]
        print({"updated": out})
        if not out:
            print({"warning": "No near-expiration rule (3-10) found to update"})
            return 2
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

