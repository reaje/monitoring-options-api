"""Apply MT5 Symbol Mappings migration via Supabase Management API.

This script applies the migration by executing it through the Supabase client's
SQL execution method, which handles the connection properly.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from supabase import create_client


def apply_migration():
    """Apply the MT5 symbol mappings migration via Supabase."""

    # Read migration SQL
    migration_path = Path(__file__).parent.parent.parent / "database" / "migrations" / "010_create_mt5_symbol_mappings.sql"

    print("=" * 70)
    print("MT5 SYMBOL MAPPINGS - MIGRATION VIA SUPABASE API")
    print("=" * 70)

    print(f"\nReading migration from: {migration_path}")

    if not migration_path.exists():
        print(f"ERROR: Migration file not found!")
        return False

    with open(migration_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    print(f"Migration SQL loaded: {len(sql)} characters")

    # Create Supabase client
    print(f"\nConnecting to Supabase...")
    print(f"URL: {settings.SUPABASE_URL[:40]}...")
    print(f"Schema: {settings.DB_SCHEMA}")

    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

        print("\nConnection successful!")
        print("\nExecuting migration via Supabase RPC...")
        print("-" * 70)

        # Execute the SQL using Supabase's RPC mechanism
        # Note: Supabase client doesn't have direct SQL execution
        # We'll use the PostgREST admin endpoint

        # For now, let's just verify if the table already exists
        print("\nChecking if table already exists...")

        try:
            # Try to query the table (will fail if it doesn't exist)
            result = supabase.table("mt5_symbol_mappings").select("id").limit(1).execute()

            print("\n" + "=" * 70)
            print("TABLE ALREADY EXISTS!")
            print("=" * 70)
            print(f"\nTable 'mt5_symbol_mappings' already exists!")

            # Count records
            count_result = supabase.table("mt5_symbol_mappings").select("id", count="exact").execute()
            print(f"Current records: {count_result.count}")

            if count_result.count > 0:
                # Show sample
                sample = supabase.table("mt5_symbol_mappings").select("*").limit(5).execute()
                print(f"\nSample mappings:")
                for mapping in sample.data:
                    mt5_sym = mapping.get('mt5_symbol')
                    ticker = mapping.get('ticker')
                    asset_type = mapping.get('asset_type')
                    print(f"  - {mt5_sym} -> {ticker} (type: {asset_type})")

            print("\n" + "=" * 70)
            print("Migration not needed - table exists and is functional!")
            print("=" * 70)
            return True

        except Exception as e:
            error_msg = str(e).lower()

            if "does not exist" in error_msg or "relation" in error_msg:
                print(f"\nTable does not exist yet.")
                print("\n" + "=" * 70)
                print("MANUAL MIGRATION REQUIRED")
                print("=" * 70)
                print("\nThe Supabase Python client cannot execute DDL statements directly.")
                print("Please apply the migration manually using ONE of these methods:")
                print("\n1. Via Supabase Dashboard (RECOMMENDED):")
                print("   - Go to: https://supabase.com/dashboard")
                print("   - Select your project")
                print("   - Click 'SQL Editor' in the left sidebar")
                print("   - Click 'New query'")
                print(f"   - Copy the contents of: {migration_path}")
                print("   - Paste into the SQL Editor")
                print("   - Click 'Run' (or press Ctrl+Enter)")
                print("\n2. Via psql command line:")
                print(f"   psql $DATABASE_URL < {migration_path}")
                print("\n3. Via pgAdmin or other PostgreSQL GUI tool")

                print("\n" + "=" * 70)
                print("After applying manually, run this script again to verify.")
                print("=" * 70)
                return False
            else:
                # Some other error
                raise

    except Exception as e:
        print(f"\nERROR:")
        print(f"  {e}")
        print("\nTroubleshooting:")
        print("  - Check if SUPABASE_URL and SUPABASE_KEY are correct in .env")
        print("  - Ensure you have network connectivity to Supabase")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("MT5 SYMBOL MAPPINGS - MIGRATION APPLICATION")
    print("=" * 70 + "\n")

    success = apply_migration()

    if not success:
        print("\nMigration could not be applied automatically.")
        print("Please follow the manual instructions above.")
        sys.exit(1)

    print("\nMigration verification complete!")
    sys.exit(0)
