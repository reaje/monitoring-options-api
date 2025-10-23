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
        server_settings={"search_path": settings.DB_SCHEMA},
    )
    try:
        await conn.execute("select set_config('request.jwt.claim.sub', $1, true)", USER_ID)
        row = await conn.fetchrow(
            f"""
            INSERT INTO {settings.DB_SCHEMA}.accounts (user_id, name, broker, account_number)
            VALUES ($1,$2,$3,$4)
            RETURNING id, user_id, name, broker, account_number, created_at
            """,
            USER_ID, "Script Conta", "XP", "999",
        )
        print("INSERT_OK:", str(row["id"]))
    except Exception as e:
        print("INSERT_ERR:", str(e))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

