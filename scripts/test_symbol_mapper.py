"""Test script for MT5 Symbol Mapper.

This script tests the symbol_mapper module's ability to:
1. Decode MT5 symbols → backend ticker info
2. Encode backend ticker info → MT5 symbols
3. Handle edge cases and validation
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from MT5.symbol_mapper import MT5SymbolMapper, get_mapper
from datetime import date


def test_decode():
    """Test decoding MT5 symbols."""
    print("=" * 70)
    print("TEST 1: Decoding MT5 Symbols -> Backend Format")
    print("=" * 70)

    mapper = get_mapper()

    test_cases = [
        # (mt5_symbol, expected_ticker, expected_type, expected_month)
        ("VALEC125", "VALE3", "call", 3),       # Vale CALL March, strike 62.50
        ("VALEQ125", "VALE3", "put", 5),        # Vale PUT May (Q=5), strike 62.50
        ("PETRJ70", "PETR4", "call", 10),       # Petrobras CALL October, strike 35.00
        ("PETRV70", "PETR4", "put", 10),        # Petrobras PUT October, strike 35.00
        ("BBASO45", "BBAS3", "put", 3),         # Banco do Brasil PUT March, strike 22.50
        ("ITUBA90", "ITUB4", "call", 1),        # Itaú CALL January, strike 45.00
        ("MGLUQ25", "MGLU3", "put", 5),         # Magazine Luiza PUT May, strike 12.50 or 0.25
    ]

    for mt5_symbol, exp_ticker, exp_type, exp_month in test_cases:
        try:
            result = mapper.decode_mt5_symbol(mt5_symbol, current_year=2024)

            status = "✅" if (
                result["ticker"] == exp_ticker and
                result["option_type"] == exp_type and
                result["month"] == exp_month
            ) else "❌"

            print(f"\n{status} {mt5_symbol}")
            print(f"   → Ticker: {result['ticker']} (expected: {exp_ticker})")
            print(f"   → Type: {result['option_type']} (expected: {exp_type})")
            print(f"   → Month: {result['month']} (expected: {exp_month})")
            print(f"   → Strike: {result['strike']}")
            print(f"   → Expiration: {result['expiration_date']}")

        except Exception as e:
            print(f"\n❌ {mt5_symbol}")
            print(f"   ERROR: {e}")

    print()


def test_encode():
    """Test encoding backend info -> MT5 symbols."""
    print("=" * 70)
    print("TEST 2: Encoding Backend Format -> MT5 Symbols")
    print("=" * 70)

    mapper = get_mapper()

    test_cases = [
        # (ticker, strike, type, expiration, expected_mt5)
        ("VALE3", 62.50, "call", date(2024, 3, 15), "VALEC125"),
        ("VALE3", 62.50, "put", date(2024, 5, 17), "VALEQ125"),
        ("PETR4", 35.00, "call", date(2024, 10, 18), "PETRJ70"),
        ("PETR4", 35.00, "put", date(2024, 10, 18), "PETRV70"),
        ("BBAS3", 22.50, "put", date(2024, 3, 15), "BBASO45"),
        ("ITUB4", 45.00, "call", date(2024, 1, 19), "ITUBA90"),
    ]

    for ticker, strike, opt_type, expiration, expected_mt5 in test_cases:
        try:
            result = mapper.encode_to_mt5(ticker, strike, opt_type, expiration)

            status = "✅" if result == expected_mt5 else "❌"

            print(f"\n{status} {ticker} strike={strike} {opt_type} exp={expiration}")
            print(f"   → MT5 Symbol: {result} (expected: {expected_mt5})")

        except Exception as e:
            print(f"\n❌ {ticker} strike={strike} {opt_type} exp={expiration}")
            print(f"   ERROR: {e}")

    print()


def test_roundtrip():
    """Test roundtrip: decode -> encode -> decode."""
    print("=" * 70)
    print("TEST 3: Roundtrip (decode -> encode -> decode)")
    print("=" * 70)

    mapper = get_mapper()

    test_symbols = ["VALEC125", "PETRJ70", "BBASO45"]

    for mt5_symbol in test_symbols:
        try:
            # Decode
            decoded = mapper.decode_mt5_symbol(mt5_symbol, current_year=2024)

            # Encode back
            encoded = mapper.encode_to_mt5(
                decoded["ticker"],
                decoded["strike"],
                decoded["option_type"],
                decoded["expiration_date"]
            )

            # Decode again
            decoded2 = mapper.decode_mt5_symbol(encoded, current_year=2024)

            status = "✅" if (
                decoded["ticker"] == decoded2["ticker"] and
                decoded["strike"] == decoded2["strike"] and
                decoded["option_type"] == decoded2["option_type"] and
                decoded["month"] == decoded2["month"]
            ) else "❌"

            print(f"\n{status} {mt5_symbol}")
            print(f"   → Decoded: {decoded['ticker']} {decoded['strike']} {decoded['option_type']} {decoded['expiration_date']}")
            print(f"   → Encoded: {encoded}")
            print(f"   → Re-decoded: {decoded2['ticker']} {decoded2['strike']} {decoded2['option_type']} {decoded2['expiration_date']}")

            if encoded != mt5_symbol:
                print(f"   ⚠️  Warning: Original symbol '{mt5_symbol}' != Encoded '{encoded}'")

        except Exception as e:
            print(f"\n❌ {mt5_symbol}")
            print(f"   ERROR: {e}")

    print()


def test_third_friday():
    """Test 3rd Friday calculation."""
    print("=" * 70)
    print("TEST 4: 3rd Friday Calculation")
    print("=" * 70)

    mapper = get_mapper()

    test_cases = [
        # (year, month, expected_day)
        (2024, 1, 19),   # January 2024 - 3rd Friday is 19th
        (2024, 3, 15),   # March 2024 - 3rd Friday is 15th
        (2024, 5, 17),   # May 2024 - 3rd Friday is 17th
        (2024, 10, 18),  # October 2024 - 3rd Friday is 18th
        (2024, 12, 20),  # December 2024 - 3rd Friday is 20th
    ]

    for year, month, expected_day in test_cases:
        try:
            third_friday = mapper._get_third_friday(year, month)

            status = "✅" if third_friday.day == expected_day else "❌"

            print(f"{status} {year}-{month:02d}: {third_friday} (expected day {expected_day})")

        except Exception as e:
            print(f"❌ {year}-{month:02d}: ERROR - {e}")

    print()


def test_edge_cases():
    """Test edge cases and error handling."""
    print("=" * 70)
    print("TEST 5: Edge Cases and Error Handling")
    print("=" * 70)

    mapper = get_mapper()

    # Invalid symbols (should raise ValueError)
    invalid_symbols = [
        "INVALID",        # Too short
        "VALE",           # No type code or strike
        "VALE3125",       # Type code '3' invalid
        "VALECC125",      # Double type code
        "VALE@125",       # Invalid character
    ]

    print("\nTesting invalid symbols (should raise ValueError):")
    for symbol in invalid_symbols:
        try:
            result = mapper.decode_mt5_symbol(symbol)
            print(f"❌ {symbol}: Expected ValueError but got result: {result}")
        except ValueError as e:
            print(f"✅ {symbol}: Correctly raised ValueError - {str(e)[:50]}...")
        except Exception as e:
            print(f"⚠️  {symbol}: Unexpected error - {type(e).__name__}: {e}")

    # Invalid encoding parameters
    print("\nTesting invalid encoding parameters:")
    invalid_encodes = [
        ("VALE3", 62.50, "invalid_type", date(2024, 3, 15)),  # Invalid option type
        ("", 62.50, "call", date(2024, 3, 15)),                # Empty ticker
    ]

    for ticker, strike, opt_type, exp_date in invalid_encodes:
        try:
            result = mapper.encode_to_mt5(ticker, strike, opt_type, exp_date)
            print(f"❌ {ticker}/{strike}/{opt_type}: Expected ValueError but got: {result}")
        except ValueError as e:
            print(f"✅ {ticker}/{strike}/{opt_type}: Correctly raised ValueError - {str(e)[:50]}...")
        except Exception as e:
            print(f"⚠️  {ticker}/{strike}/{opt_type}: Unexpected error - {type(e).__name__}: {e}")

    print()


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("MT5 SYMBOL MAPPER - TEST SUITE")
    print("=" * 70 + "\n")

    test_decode()
    test_encode()
    test_roundtrip()
    test_third_friday()
    test_edge_cases()

    print("=" * 70)
    print("TEST SUITE COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
