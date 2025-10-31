"""Apply MT5 Symbol Mappings migration to Supabase.

This script reads the migration SQL file and applies it to the database.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from supabase import create_client


def apply_migration():
    """Apply the MT5 symbol mappings migration."""

    # Read migration SQL
    migration_path = Path(__file__).parent.parent.parent / "database" / "migrations" / "010_create_mt5_symbol_mappings.sql"

    print(f"Reading migration from: {migration_path}")

    if not migration_path.exists():
        print(f"ERROR: Migration file not found at {migration_path}")
        return False

    with open(migration_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    print(f"Migration SQL loaded ({len(sql)} characters)")

    # Create Supabase client
    print(f"Connecting to Supabase...")
    print(f"URL: {settings.SUPABASE_URL[:30]}...")
    print(f"Schema: {settings.DB_SCHEMA}")

    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    # Execute migration using raw SQL
    # Note: Supabase client doesn't have a direct "execute SQL" method for DDL
    # We need to use the REST API or PostgREST

    print("\n" + "="*70)
    print("IMPORTANT: SQL migration needs to be applied manually")
    print("="*70)
    print("\nThe migration SQL is ready at:")
    print(f"  {migration_path}")
    print("\nOptions to apply:")
    print("\n1. Via Supabase Dashboard:")
    print("   - Go to https://supabase.com/dashboard")
    print("   - Select your project")
    print("   - Go to SQL Editor")
    print("   - Paste the SQL from the migration file")
    print("   - Run the query")

    print("\n2. Via psql command line:")
    print("   psql $DATABASE_URL < database/migrations/010_create_mt5_symbol_mappings.sql")

    print("\n3. Via Python with psycopg2:")
    print("   (requires DATABASE_URL with direct Postgres connection)")

    # Try to verify if table already exists
    try:
        print("\n" + "="*70)
        print("Checking if table already exists...")
        print("="*70)

        # Try to query the table (will fail if it doesn't exist)
        result = supabase.table("mt5_symbol_mappings").select("id").limit(1).execute()

        print("\n✅ Table 'mt5_symbol_mappings' ALREADY EXISTS!")
        print(f"   Current records: checking...")

        # Count records
        count_result = supabase.table("mt5_symbol_mappings").select("id", count="exact").execute()
        print(f"   Total mappings: {count_result.count}")

        if count_result.count > 0:
            # Show sample
            sample = supabase.table("mt5_symbol_mappings").select("*").limit(5).execute()
            print(f"\n   Sample mappings:")
            for mapping in sample.data:
                print(f"     - {mapping.get('mt5_symbol')} → {mapping.get('ticker')} (type: {mapping.get('asset_type')})")

        return True

    except Exception as e:
        print(f"\n⚠️  Table does not exist yet or error accessing it:")
        print(f"   {str(e)}")
        print("\n   Please apply the migration manually using one of the methods above.")
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("MT5 SYMBOL MAPPINGS - MIGRATION APPLICATION")
    print("="*70 + "\n")

    success = apply_migration()

    print("\n" + "="*70)
    if success:
        print("✅ Migration check complete - Table exists!")
    else:
        print("⚠️  Manual migration application required")
    print("="*70 + "\n")
