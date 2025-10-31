"""Check if mt5_symbol_mappings table exists and show details."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from supabase import create_client


def check_table():
    """Check table existence and details."""

    print("=" * 70)
    print("MT5 TABLE CHECK")
    print("=" * 70)

    print(f"\nConfiguration:")
    print(f"  SUPABASE_URL: {settings.SUPABASE_URL[:40]}...")
    print(f"  DB_SCHEMA: {settings.DB_SCHEMA}")

    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    # Try different approaches to check if table exists

    # Approach 1: Try to select from public schema
    print("\n" + "-" * 70)
    print("Approach 1: Query from 'public' schema")
    print("-" * 70)
    try:
        result = supabase.schema("public").table("mt5_symbol_mappings").select("id").limit(1).execute()
        print(f"SUCCESS - Table exists in 'public' schema!")
        print(f"  Found {len(result.data)} records")
        return True
    except Exception as e:
        print(f"NOT FOUND in 'public': {str(e)[:100]}")

    # Approach 2: Try to select from monitoring_options_operations schema
    print("\n" + "-" * 70)
    print("Approach 2: Query from 'monitoring_options_operations' schema")
    print("-" * 70)
    try:
        result = supabase.schema("monitoring_options_operations").table("mt5_symbol_mappings").select("id").limit(1).execute()
        print(f"SUCCESS - Table exists in 'monitoring_options_operations' schema!")
        print(f"  Found {len(result.data)} records")
        return True
    except Exception as e:
        print(f"NOT FOUND in 'monitoring_options_operations': {str(e)[:100]}")

    # Approach 3: Try without specifying schema (default)
    print("\n" + "-" * 70)
    print("Approach 3: Query without schema specification")
    print("-" * 70)
    try:
        result = supabase.table("mt5_symbol_mappings").select("id").limit(1).execute()
        print(f"SUCCESS - Table exists (default schema)!")
        print(f"  Found {len(result.data)} records")
        return True
    except Exception as e:
        error_msg = str(e)
        print(f"NOT FOUND: {error_msg[:200]}")

        # Parse error message to understand what's wrong
        if "does not exist" in error_msg.lower():
            print("\nDIAGNOSTIC: Table truly doesn't exist yet")
        elif "permission" in error_msg.lower():
            print("\nDIAGNOSTIC: Permission issue - check RLS policies")
        elif "schema" in error_msg.lower():
            print("\nDIAGNOSTIC: Schema issue - table might be in different schema")

    # Approach 4: Try to query information_schema (if accessible)
    print("\n" + "-" * 70)
    print("Approach 4: Check information_schema")
    print("-" * 70)
    try:
        # This won't work with Supabase client, but let's try
        result = supabase.rpc("get_tables_info").execute()
        print(f"Tables info: {result.data}")
    except Exception as e:
        print(f"Cannot query information_schema: {str(e)[:100]}")

    print("\n" + "=" * 70)
    print("TABLE NOT FOUND IN ANY SCHEMA")
    print("=" * 70)
    print("\nPossible reasons:")
    print("  1. Migration not yet applied")
    print("  2. Table created in unexpected schema")
    print("  3. RLS policies blocking access")
    print("  4. Supabase client cache issue")

    print("\nRecommended actions:")
    print("  1. Check Supabase Dashboard -> Table Editor")
    print("  2. Check SQL Editor for any error messages")
    print("  3. Try running migration again")
    print("  4. Verify you're connected to correct project")

    return False


if __name__ == "__main__":
    success = check_table()
    sys.exit(0 if success else 1)
