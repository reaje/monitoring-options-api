"""Verify MT5 migration was applied successfully.

This script checks if the table exists by querying it directly,
not through the Supabase client's schema method.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
import psycopg2


def verify_migration():
    """Verify the migration was applied."""

    print("=" * 70)
    print("MT5 MIGRATION VERIFICATION")
    print("=" * 70)

    # Parse DATABASE_URL to get connection params
    database_url = settings.DATABASE_URL

    if not database_url:
        print("\nERROR: DATABASE_URL not set in environment")
        return False

    print(f"\nDatabase URL length: {len(database_url)} characters")
    print(f"Schema: {settings.DB_SCHEMA}")

    # Try to connect and query directly
    try:
        # For Supabase URLs with query parameters, we need to parse them out
        # The format is: postgresql://user:pass@host:port/db?param=value

        # Remove query parameters for psycopg2
        if "?" in database_url:
            base_url = database_url.split("?")[0]
            print(f"\nUsing base URL (without query params) for connection")
        else:
            base_url = database_url

        print(f"\nConnecting to database...")

        conn = psycopg2.connect(base_url)
        cursor = conn.cursor()

        print("Connection successful!")

        # Set search path to our schema
        cursor.execute(f"SET search_path TO {settings.DB_SCHEMA}, public")

        # Check if table exists
        print(f"\nChecking if table exists in '{settings.DB_SCHEMA}' schema...")

        cursor.execute(f"""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = '{settings.DB_SCHEMA}'
            AND table_name = 'mt5_symbol_mappings'
        """)

        count = cursor.fetchone()[0]

        if count > 0:
            print(f"\n" + "=" * 70)
            print("SUCCESS - TABLE EXISTS!")
            print("=" * 70)

            # Get table details
            cursor.execute(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = '{settings.DB_SCHEMA}'
                AND table_name = 'mt5_symbol_mappings'
                ORDER BY ordinal_position
            """)

            columns = cursor.fetchall()
            print(f"\nTable structure ({len(columns)} columns):")
            for col_name, col_type in columns:
                print(f"  - {col_name}: {col_type}")

            # Count records
            cursor.execute(f"SELECT COUNT(*) FROM {settings.DB_SCHEMA}.mt5_symbol_mappings")
            record_count = cursor.fetchone()[0]
            print(f"\nTotal records: {record_count}")

            if record_count > 0:
                # Show sample data
                cursor.execute(f"""
                    SELECT mt5_symbol, ticker, asset_type, strike, option_type
                    FROM {settings.DB_SCHEMA}.mt5_symbol_mappings
                    LIMIT 5
                """)

                print(f"\nSample data:")
                for row in cursor.fetchall():
                    mt5_sym, ticker, asset_type, strike, opt_type = row
                    if asset_type == 'stock':
                        print(f"  - {mt5_sym} -> {ticker} (stock)")
                    else:
                        print(f"  - {mt5_sym} -> {ticker} strike={strike} {opt_type}")

            # Check indexes
            cursor.execute(f"""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = '{settings.DB_SCHEMA}'
                AND tablename = 'mt5_symbol_mappings'
            """)

            indexes = cursor.fetchall()
            print(f"\nIndexes ({len(indexes)}):")
            for (idx_name,) in indexes:
                print(f"  - {idx_name}")

            print("\n" + "=" * 70)
            print("MIGRATION VERIFIED SUCCESSFULLY!")
            print("=" * 70)
            print("\nThe mt5_symbol_mappings table is ready to use.")
            print("Backend MT5 Bridge Fase 2 is 100% ready!")

            cursor.close()
            conn.close()
            return True

        else:
            print(f"\n" + "=" * 70)
            print("TABLE NOT FOUND")
            print("=" * 70)
            print(f"\nTable 'mt5_symbol_mappings' does not exist in schema '{settings.DB_SCHEMA}'")
            print("\nPlease apply the migration via Supabase Dashboard SQL Editor.")

            cursor.close()
            conn.close()
            return False

    except psycopg2.Error as e:
        print(f"\nDatabase error:")
        print(f"  {e}")

        # Check if it's a connection string parse error
        if "invalid dsn" in str(e).lower():
            print("\nTrying alternate connection method...")

            # If the URL has search_path, it might cause issues
            # Let's try without it
            try:
                # Extract just the base connection components
                import re
                match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/([^\?]+)', database_url)
                if match:
                    user, password, host, port, dbname = match.groups()
                    conn = psycopg2.connect(
                        host=host,
                        port=port,
                        database=dbname,
                        user=user,
                        password=password
                    )
                    print("Connected with alternate method!")

                    # Retry the queries above
                    cursor = conn.cursor()
                    cursor.execute(f"SET search_path TO {settings.DB_SCHEMA}, public")

                    cursor.execute(f"""
                        SELECT COUNT(*)
                        FROM information_schema.tables
                        WHERE table_schema = '{settings.DB_SCHEMA}'
                        AND table_name = 'mt5_symbol_mappings'
                    """)

                    count = cursor.fetchone()[0]

                    if count > 0:
                        print(f"\nTABLE EXISTS! (Found via alternate connection)")
                        cursor.close()
                        conn.close()
                        return True

            except Exception as e2:
                print(f"Alternate method also failed: {e2}")

        return False

    except Exception as e:
        print(f"\nUnexpected error:")
        print(f"  {e}")
        return False


if __name__ == "__main__":
    success = verify_migration()

    if success:
        print("\nYou can now proceed with the next steps:")
        print("  - Implement JsonHelper.mqh for option quotes")
        print("  - Update VentryBridge.mq5 EA")
        print("  - Test with real MT5 terminal")
        sys.exit(0)
    else:
        print("\nMigration verification failed.")
        print("Please check Supabase Dashboard to confirm the migration was applied.")
        sys.exit(1)
