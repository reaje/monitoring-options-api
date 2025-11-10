"""MT5 Symbol Mapper - Converts between MT5 symbols and backend ticker information.

This module handles the bidirectional mapping between MetaTrader 5 option symbols
and the backend's ticker/strike/expiration format.

MT5 Option Symbol Format (Brazilian market - B3):
    [TICKER][TYPE][STRIKE]

    Where:
    - TICKER: 4-5 letters (VALE, PETR, BBAS, etc)
    - TYPE: 1 letter indicating month + CALL/PUT
        - A-L = CALL (A=Jan, B=Feb, ..., L=Dec)
        - M-X = PUT (M=Jan, N=Feb, ..., X=Dec)
    - STRIKE: Strike price * 100, no decimal point
        - Ex: 125 = R$ 1.25 or R$ 62.50 (depends on context/scale)

Examples:
    - VALEC125 → VALE3, CALL, March, strike 62.50
    - PETRJ70  → PETR4, CALL, October, strike 35.00
    - BBASO45  → BBAS3, PUT, March, strike 22.50

Note: The strike price scaling (divide by 100 vs divide by 10) depends on
the underlying asset's typical price range. This mapper handles both cases.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional, Dict, Any
from calendar import monthrange
from app.core.logger import logger


class MT5SymbolMapper:
    """Mapper for MT5 symbols ↔ backend ticker information."""

    # Month codes for CALL options (A-L)
    MONTH_CODES_CALL = {
        'A': 1, 'B': 2, 'C': 3, 'D': 4,
        'E': 5, 'F': 6, 'G': 7, 'H': 8,
        'I': 9, 'J': 10, 'K': 11, 'L': 12
    }

    # Month codes for PUT options (M-X)
    MONTH_CODES_PUT = {
        'M': 1, 'N': 2, 'O': 3, 'P': 4,
        'Q': 5, 'R': 6, 'S': 7, 'T': 8,
        'U': 9, 'V': 10, 'W': 11, 'X': 12
    }

    # Reverse mappings (month → code)
    CALL_CODE_BY_MONTH = {v: k for k, v in MONTH_CODES_CALL.items()}
    PUT_CODE_BY_MONTH = {v: k for k, v in MONTH_CODES_PUT.items()}

    # Common Brazilian stock tickers and their typical suffixes
    TICKER_SUFFIXES = {
        'VALE': 'VALE3',
        'PETR': 'PETR4',
        'BBAS': 'BBAS3',
        'ITUB': 'ITUB4',
        'BBDC': 'BBDC4',
        'ABEV': 'ABEV3',
        'MGLU': 'MGLU3',
        'WEGE': 'WEGE3',
        'RENT': 'RENT3',
        'GGBR': 'GGBR4',
        'USIM': 'USIM5',
        'CSNA': 'CSNA3',
        'SUZB': 'SUZB3',
        'EMBR': 'EMBR3',
        'CIEL': 'CIEL3',
    }

    def __init__(self):
        """Initialize the mapper."""
        pass

    def decode_mt5_symbol(self, mt5_symbol: str, current_year: Optional[int] = None) -> Dict[str, Any]:
        """
        Decode MT5 option symbol into components.

        Args:
            mt5_symbol: MT5 symbol (e.g., "VALEC125", "PETRJ70")
            current_year: Year to use for expiration calculation (default: current year)

        Returns:
            Dictionary with:
                - ticker: Backend ticker (e.g., "VALE3")
                - strike: Strike price as float
                - option_type: "call" or "put"
                - month: Month number (1-12)
                - year: Inferred year
                - expiration_date: Expiration date (3rd Friday)
                - mt5_symbol: Original symbol

        Raises:
            ValueError: If symbol cannot be decoded
        """
        mt5_symbol = mt5_symbol.strip().upper()

        # Pattern: [TICKER][TYPE_CODE][STRIKE_DIGITS][OPTIONAL_SUFFIX]
        # Example: VALEC125 → VALE + C + 125
        # Aceita sufixos após os dígitos (ex.: "W1", "W2"): BBASK215W2, VALEK645W1
        match = re.match(r'^([A-Z]{4,5})([A-X])(\d+)([A-Z0-9]*)$', mt5_symbol)

        if not match:
            raise ValueError(f"Invalid MT5 option symbol format: {mt5_symbol}")

        ticker_base, type_code, strike_str, _suffix = match.groups()

        # Determine option type and month
        if type_code in self.MONTH_CODES_CALL:
            option_type = "call"
            month = self.MONTH_CODES_CALL[type_code]
        elif type_code in self.MONTH_CODES_PUT:
            option_type = "put"
            month = self.MONTH_CODES_PUT[type_code]
        else:
            raise ValueError(f"Invalid type code '{type_code}' in symbol {mt5_symbol}")

        # Convert ticker_base to full ticker (e.g., VALE → VALE3)
        ticker = self._normalize_ticker(ticker_base)

        # Decode strike price
        strike = self._decode_strike(strike_str, ticker)

        # Calculate expiration year
        year = current_year or datetime.now().year
        expiration_month = month

        # If the expiration month is in the past, assume next year
        current_month = datetime.now().month
        if expiration_month < current_month:
            year += 1

        # Calculate 3rd Friday of the month
        expiration_date = self._get_third_friday(year, expiration_month)

        result = {
            "mt5_symbol": mt5_symbol,
            "ticker": ticker,
            "strike": strike,
            "option_type": option_type,
            "month": month,
            "year": year,
            "expiration_date": expiration_date.isoformat(),
        }

        logger.debug("mt5_mapper.decode", symbol=mt5_symbol, result=result)
        return result

    def encode_to_mt5(
        self,
        ticker: str,
        strike: float,
        option_type: str,
        expiration_date: date | str,
    ) -> str:
        """
        Encode backend ticker info into MT5 symbol.

        Args:
            ticker: Backend ticker (e.g., "VALE3")
            strike: Strike price as float
            option_type: "call" or "put"
            expiration_date: Expiration date (date object or ISO string)

        Returns:
            MT5 symbol string (e.g., "VALEC125")

        Raises:
            ValueError: If encoding fails
        """
        ticker = ticker.strip().upper()
        option_type = option_type.strip().lower()

        if option_type not in ("call", "put"):
            raise ValueError(f"Invalid option_type: {option_type}. Must be 'call' or 'put'")

        # Convert expiration_date to date object if string
        if isinstance(expiration_date, str):
            expiration_date = date.fromisoformat(expiration_date)

        month = expiration_date.month

        # Get type code for the month
        if option_type == "call":
            if month not in self.CALL_CODE_BY_MONTH:
                raise ValueError(f"Invalid month {month} for CALL")
            type_code = self.CALL_CODE_BY_MONTH[month]
        else:  # put
            if month not in self.PUT_CODE_BY_MONTH:
                raise ValueError(f"Invalid month {month} for PUT")
            type_code = self.PUT_CODE_BY_MONTH[month]

        # Get ticker base (remove suffix: VALE3 → VALE)
        ticker_base = self._get_ticker_base(ticker)

        # Encode strike
        strike_code = self._encode_strike(strike)

        mt5_symbol = f"{ticker_base}{type_code}{strike_code}"

        logger.debug(
            "mt5_mapper.encode",
            ticker=ticker,
            strike=strike,
            option_type=option_type,
            expiration=expiration_date.isoformat(),
            mt5_symbol=mt5_symbol,
        )

        return mt5_symbol

    def _normalize_ticker(self, ticker_base: str) -> str:
        """
        Convert ticker base to full ticker with suffix.

        Args:
            ticker_base: Base ticker (e.g., "VALE")

        Returns:
            Full ticker (e.g., "VALE3")
        """
        ticker_base = ticker_base.strip().upper()

        # If already has suffix (ends with digit), return as-is
        if ticker_base and ticker_base[-1].isdigit():
            return ticker_base

        # Look up in known suffixes
        if ticker_base in self.TICKER_SUFFIXES:
            return self.TICKER_SUFFIXES[ticker_base]

        # Default: assume PN (most common) = suffix "3"
        return f"{ticker_base}3"

    def _get_ticker_base(self, ticker: str) -> str:
        """
        Extract ticker base by removing numeric suffix.

        Args:
            ticker: Full ticker (e.g., "VALE3", "PETR4")

        Returns:
            Ticker base (e.g., "VALE", "PETR")
        """
        ticker = ticker.strip().upper()

        # Remove trailing digits
        return re.sub(r'\d+$', '', ticker)

    def _decode_strike(self, strike_str: str, ticker: str) -> float:
        """
        Decode strike price from MT5 strike code.

        The strike encoding in MT5 varies:
        - For high-price stocks (VALE3 ~R$60): divide by 2
        - For mid-price stocks (PETR4 ~R$35): divide by 2
        - For low-price stocks (MGLU3 ~R$1): divide by 100

        This method uses heuristics to determine the correct scaling.

        Args:
            strike_str: Strike code from MT5 symbol (e.g., "125", "70")
            ticker: Full ticker (for context)

        Returns:
            Strike price as float
        """
        strike_int = int(strike_str)

        # Heuristic: If strike_int is > 1000, it's likely encoded with /100
        # If strike_int is < 1000, it's likely encoded with /2
        if strike_int >= 1000:
            # Low-price stock: divide by 100
            # Example: 125 → 1.25
            return strike_int / 100.0
        else:
            # High/mid-price stock: divide by 2
            # Example: 125 → 62.50, 70 → 35.00
            return strike_int / 2.0

    def _encode_strike(self, strike: float) -> str:
        """
        Encode strike price to MT5 strike code.

        Args:
            strike: Strike price as float

        Returns:
            Strike code string (e.g., "125" for 62.50)
        """
        # Heuristic: If strike < 10.0, use *100 encoding
        # Otherwise, use *2 encoding
        if strike < 10.0:
            # Low-price stock: multiply by 100
            strike_int = int(strike * 100)
        else:
            # High/mid-price stock: multiply by 2
            strike_int = int(strike * 2)

        return str(strike_int)

    def _get_third_friday(self, year: int, month: int) -> date:
        """
        Calculate the 3rd Friday of a given month/year.

        This is the standard expiration date for monthly options on B3.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Date object representing the 3rd Friday
        """
        # Get the first day of the month
        first_day = date(year, month, 1)

        # Find the first Friday
        # weekday(): Monday=0, ..., Friday=4
        days_until_friday = (4 - first_day.weekday()) % 7
        first_friday = first_day.day + days_until_friday

        # 3rd Friday = first Friday + 14 days
        third_friday_day = first_friday + 14

        # Ensure we don't exceed the month
        _, last_day = monthrange(year, month)
        if third_friday_day > last_day:
            raise ValueError(f"Invalid 3rd Friday calculation for {year}-{month:02d}")

        return date(year, month, third_friday_day)


# Global singleton instance
_mapper_instance: Optional[MT5SymbolMapper] = None


def get_mapper() -> MT5SymbolMapper:
    """Get the global MT5SymbolMapper instance."""
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = MT5SymbolMapper()
    return _mapper_instance
