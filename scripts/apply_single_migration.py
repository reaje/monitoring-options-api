"""Apply a single SQL migration file by path.

Usage:
    python scripts/apply_single_migration.py <relative_path_to_sql>

Example:
    python scripts/apply_single_migration.py ../database/migrations/006_add_broker_account_number_to_accounts.sql
"""
from __future__ import annotations

import sys
from pathlib import Path
import asyncio
import asyncpg

# Ensure we can import app.config
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import settings  # noqa: E402
from app.core.logger import logger  # noqa: E402


async def apply_sql_file(sql_path: Path) -> None:
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    sql = sql_path.read_text(encoding="utf-8")

    logger.info("Connecting to database to run single migration...", file=str(sql_path))
    conn = await asyncpg.connect(settings.DATABASE_URL)
    try:
        await conn.execute(sql)
        logger.info("Single migration executed successfully", file=str(sql_path))
    finally:
        await conn.close()
        logger.info("Database connection closed")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/apply_single_migration.py <path_to_sql>")
        return 2

    sql_rel = sys.argv[1]
    base = Path(__file__).resolve().parent.parent
    sql_path = (base / sql_rel).resolve() if not sql_rel.endswith('.sql') else Path(sql_rel).resolve()

    try:
        asyncio.run(apply_sql_file(sql_path))
    except Exception as e:
        logger.error("Failed to apply single migration", error=str(e))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

