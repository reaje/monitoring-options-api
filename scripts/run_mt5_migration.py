"""Run MT5 Symbol Mappings migration directly using psycopg2."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
import psycopg2


def run_migration():
    """Run the migration SQL directly."""

    # Read migration SQL
    migration_path = Path(__file__).parent.parent.parent / "database" / "migrations" / "010_create_mt5_symbol_mappings.sql"

    print("=" * 70)
    print("MT5 SYMBOL MAPPINGS - MIGRATION")
    print("=" * 70)

    print(f"\nReading migration from: {migration_path}")

    if not migration_path.exists():
        print(f"ERROR: Migration file not found!")
        return False

    with open(migration_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    print(f"Migration SQL loaded: {len(sql)} characters")

    # Connect to database
    database_url = settings.DATABASE_URL

    if not database_url:
        print("\nERROR: DATABASE_URL not configured!")
        print("Please set DATABASE_URL in your .env file")
        return False

    print(f"\nConnecting to database...")
    print(f"Schema: {settings.DB_SCHEMA}")

    try:
        # Connect
        conn = psycopg2.connect(database_url)
        conn.autocommit = True  # Important for DDL
        cursor = conn.cursor()

        print("\nConnection successful!")
        print("\nExecuting migration...")
        print("-" * 70)

        # Execute migration
        cursor.execute(sql)

        print("\n" + "=" * 70)
        print("MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 70)

        # Verify table creation
        print("\nVerifying table creation...")
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = '{settings.DB_SCHEMA}'
            AND table_name = 'mt5_symbol_mappings'
        """)

        count = cursor.fetchone()[0]

        if count > 0:
            print(f"Table 'mt5_symbol_mappings' exists in schema '{settings.DB_SCHEMA}'")

            # Count seed data
            cursor.execute(f"SELECT COUNT(*) FROM {settings.DB_SCHEMA}.mt5_symbol_mappings")
            records = cursor.fetchone()[0]
            print(f"Initial records (seed data): {records}")

            # Show sample
            if records > 0:
                cursor.execute(f"""
                    SELECT mt5_symbol, ticker, asset_type, strike, option_type
                    FROM {settings.DB_SCHEMA}.mt5_symbol_mappings
                    LIMIT 5
                """)
                print("\nSample mappings:")
                for row in cursor.fetchall():
                    mt5_sym, ticker, asset_type, strike, opt_type = row
                    if asset_type == 'stock':
                        print(f"  - {mt5_sym} -> {ticker} (stock)")
                    else:
                        print(f"  - {mt5_sym} -> {ticker} strike={strike} {opt_type}")

            print("\n" + "=" * 70)
            print("Table ready to use!")
            print("=" * 70)

            return True
        else:
            print("WARNING: Table not found after migration!")
            return False

    except psycopg2.Error as e:
        print(f"\nERROR during migration:")
        print(f"  {e}")
        print("\nTroubleshooting:")
        print("  - Check if DATABASE_URL is correct")
        print("  - Ensure you have CREATE TABLE permissions")
        print("  - Verify the schema exists")
        return False

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            print("\nDatabase connection closed.")


if __name__ == "__main__":
    success = run_migration()

    if not success:
        print("\nMigration failed or could not be verified.")
        print("You may need to apply it manually via Supabase Dashboard.")
        sys.exit(1)

    print("\nMigration complete! You can now use the mt5_symbol_mappings table.")
    sys.exit(0)
