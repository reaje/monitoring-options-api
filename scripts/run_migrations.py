"""Script to run database migrations."""

import sys
import os
from pathlib import Path
import asyncio
import asyncpg

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.core.logger import logger


async def run_migrations():
    """Run all SQL migration files in order."""

    # Connect to database
    logger.info("Connecting to database...")

    conn = await asyncpg.connect(settings.DATABASE_URL)

    try:
        # Get migrations directory
        migrations_dir = Path(__file__).parent.parent.parent / "database" / "migrations"

        if not migrations_dir.exists():
            logger.error(f"Migrations directory not found: {migrations_dir}")
            return

        # Get all SQL files sorted by name
        migration_files = sorted(migrations_dir.glob("*.sql"))

        if not migration_files:
            logger.warning("No migration files found")
            return

        logger.info(f"Found {len(migration_files)} migration files")

        # Run each migration
        for migration_file in migration_files:
            logger.info(f"Running migration: {migration_file.name}")

            # Read migration file
            sql = migration_file.read_text(encoding="utf-8")

            try:
                # Execute migration
                await conn.execute(sql)
                logger.info(f"Migration {migration_file.name} completed successfully")

            except Exception as e:
                logger.error(f"Migration {migration_file.name} failed: {str(e)}")
                raise

        logger.info("All migrations completed successfully!")

    finally:
        # Close connection
        await conn.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    try:
        asyncio.run(run_migrations())
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)
