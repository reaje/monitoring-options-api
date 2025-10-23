"""Quick SQL runner using asyncpg and backend settings.

Usage:
  python scripts/quick_sql.py "SQL..." [json-args]
Examples:
  python scripts/quick_sql.py "select current_schema(), current_user" 
  python scripts/quick_sql.py "insert into monitoring_options_operations.accounts (user_id,name,broker,account_number) values($1,$2,$3,$4) returning id" '{"user_id":"2c7f91eb-5ef0-401c-a756-b8fe04cd16c3","name":"Test","broker":"XP","account_number":"123"}'
"""
from __future__ import annotations
import sys, json, asyncio
from pathlib import Path
import asyncpg

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import settings  # noqa: E402


async def run(sql: str, args: list | tuple | None):
    conn = await asyncpg.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        server_settings={"search_path": settings.DB_SCHEMA},
    )
    try:
        try:
            if args:
                res = await conn.fetch(sql, *args)
            else:
                res = await conn.fetch(sql)
            print({"rows": [dict(r) for r in res]})
        except Exception as e:
            print({"error": str(e)})
    finally:
        await conn.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/quick_sql.py \"SQL\" [json-args]")
        return 2
    sql = sys.argv[1]
    args = None
    if len(sys.argv) > 2:
        a = json.loads(sys.argv[2])
        if isinstance(a, dict):
            # Keep insertion order when possible
            args = list(a.values())
        elif isinstance(a, list):
            args = a
    asyncio.run(run(sql, args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

