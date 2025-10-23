"""Inspect accounts table columns and RLS policies.
Usage:
  python scripts/inspect_accounts_schema.py
"""
from __future__ import annotations
import asyncio
import asyncpg
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import settings  # noqa: E402
from app.core.logger import logger  # noqa: E402


async def main() -> None:
    conn = await asyncpg.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        server_settings={"search_path": settings.DB_SCHEMA},
    )
    try:
        cols = await conn.fetch(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = $1 AND table_name = 'accounts'
            ORDER BY ordinal_position
            """,
            settings.DB_SCHEMA,
        )
        logger.info("accounts.columns", columns=[dict(r) for r in cols])

        # Check if policies exist
        pols = await conn.fetch(
            """
            SELECT pol.polname as policy_name, pol.polpermissive as permissive, pg_get_expr(pol.polqual, pol.polrelid) as using
            FROM pg_policy pol
            JOIN pg_class tab ON tab.oid = pol.polrelid
            JOIN pg_namespace ns ON ns.oid = tab.relnamespace
            WHERE ns.nspname = $1 AND tab.relname = 'accounts'
            ORDER BY pol.polname
            """,
            settings.DB_SCHEMA,
        )
        logger.info("accounts.policies", policies=[dict(r) for r in pols])
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

