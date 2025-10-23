from __future__ import annotations
import asyncio
from pathlib import Path
import sys
import asyncpg

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import settings  # noqa: E402

USER_ID = "2c7f91eb-5ef0-401c-a756-b8fe04cd16c3"


async def main():
    conn = await asyncpg.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        server_settings={"search_path": settings.DB_SCHEMA, "request.jwt.claim.sub": USER_ID, "request.jwt.claim.role": "authenticated"},
    )
    try:
        rows = await conn.fetch(
            f"SELECT id, user_id, name, broker, account_number, created_at FROM {settings.DB_SCHEMA}.accounts WHERE user_id = $1 ORDER BY created_at DESC",
            USER_ID,
        )
        print("COUNT:", len(rows))
        for r in rows:
            print(dict(r))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

