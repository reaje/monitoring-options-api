"""In-memory storage/cache for MT5 bridge (Fase 1).

Provides simple persistence for last heartbeats and quotes received from the
MQL5 EA via /api/mt5 endpoints. Designed to be stateless across processes
(in production consider backing with DB/Redis if you scale horizontally).
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime, timezone
import threading

from app.config import settings

# Locks for thread-safety in Sanic worker threads
_lock = threading.RLock()

# Last heartbeat per terminal_id
_HEARTBEATS: Dict[str, Dict[str, Any]] = {}

# Last quote per symbol (uppercase)
_QUOTES: Dict[str, Dict[str, Any]] = {}

# Last option quote per option key (ticker_strike_type_expiration)
_OPTIONS_QUOTES: Dict[str, Dict[str, Any]] = {}

# Config
QUOTE_TTL_SECONDS = int(getattr(settings, "MT5_BRIDGE_QUOTE_TTL_SECONDS", 10))


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_ts_iso(ts: Optional[str]) -> datetime:
    if not ts:
        return datetime.now(timezone.utc)
    try:
        # Accept both Z and with offset
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def upsert_heartbeat(payload: Dict[str, Any]) -> None:
    terminal_id = str(payload.get("terminal_id") or "").strip() or "UNKNOWN"
    entry = {
        "terminal_id": terminal_id,
        "account_number": payload.get("account_number"),
        "broker": payload.get("broker"),
        "build": payload.get("build"),
        "ts": payload.get("timestamp") or _utcnow_iso(),
        "updated_at": _utcnow_iso(),
    }
    with _lock:
        _HEARTBEATS[terminal_id] = entry


def get_last_heartbeat(terminal_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        return _HEARTBEATS.get(terminal_id)



def get_all_heartbeats(max_age_seconds: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
    """Retorna todos os heartbeats (opcionalmente filtrados por idade)."""
    now = datetime.now(timezone.utc)
    with _lock:
        if max_age_seconds is None:
            return {k: dict(v) for k, v in _HEARTBEATS.items()}
        result: Dict[str, Dict[str, Any]] = {}
        for term_id, entry in _HEARTBEATS.items():
            ts = _parse_ts_iso(entry.get("updated_at") or entry.get("ts"))
            age = (now - ts).total_seconds()
            if age <= max_age_seconds:
                result[term_id] = dict(entry)
        return result


def upsert_quotes(payload: Dict[str, Any]) -> int:
    quotes = payload.get("quotes") or []
    terminal_id = payload.get("terminal_id")
    account_number = payload.get("account_number")
    accepted = 0
    now_iso = _utcnow_iso()

    with _lock:
        for q in quotes:
            sym = str(q.get("symbol") or q.get("ticker") or "").upper().strip()
            if not sym:
                continue
            last = q.get("last")
            # Fallbacks if EA sends only bid/ask or mid
            current_price = q.get("current_price") or last or q.get("mid") or q.get("bid") or q.get("ask")
            entry = {
                "symbol": sym,
                "bid": _safe_float(q.get("bid")),
                "ask": _safe_float(q.get("ask")),
                "last": _safe_float(last if last is not None else current_price),
                "volume": _safe_float(q.get("volume")),
                "source": "mt5",
                "ts": q.get("ts") or q.get("timestamp") or now_iso,
                "terminal_id": terminal_id,
                "account_number": account_number,
                "updated_at": now_iso,
            }
            _QUOTES[sym] = entry
            accepted += 1

    return accepted




def get_all_quotes(max_age_seconds: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
    """Retorna todas as cotações de subjacentes (opcionalmente filtradas por idade)."""
    now = datetime.now(timezone.utc)
    with _lock:
        if max_age_seconds is None:
            return {k: dict(v) for k, v in _QUOTES.items()}
        result: Dict[str, Dict[str, Any]] = {}
        for sym, entry in _QUOTES.items():
            ts = _parse_ts_iso(entry.get("ts"))
            age = (now - ts).total_seconds()
            if age <= max_age_seconds:
                result[sym] = dict(entry)
        return result

def get_latest_quote(symbol: str, ttl_seconds: Optional[int] = None) -> Optional[Dict[str, Any]]:
    sym = (symbol or "").upper().strip()
    if not sym:
        return None
    ttl = int(ttl_seconds or QUOTE_TTL_SECONDS)
    now = datetime.now(timezone.utc)
    with _lock:
        entry = _QUOTES.get(sym)
        if not entry:
            return None
        ts = _parse_ts_iso(entry.get("ts"))
        age = (now - ts).total_seconds()
        if age > ttl:
            return None
        return dict(entry)


def upsert_option_quotes(payload: Dict[str, Any]) -> int:
    """
    Store option quotes received from MT5.

    Args:
        payload: Dict with structure:
            {
                "terminal_id": "MT5-WS-01",
                "account_number": "4472007",
                "option_quotes": [
                    {
                        "mt5_symbol": "VALEC125",
                        "ticker": "VALE3",
                        "strike": 62.50,
                        "option_type": "call",
                        "expiration": "2024-03-15",
                        "bid": 2.50,
                        "ask": 2.55,
                        "last": 2.52,
                        "volume": 1000,
                        "ts": "2024-10-31T14:30:00Z"
                    }
                ]
            }

    Returns:
        Number of quotes accepted
    """
    quotes = payload.get("option_quotes") or []
    terminal_id = payload.get("terminal_id")
    account_number = payload.get("account_number")
    accepted = 0
    now_iso = _utcnow_iso()

    with _lock:
        for q in quotes:
            ticker = str(q.get("ticker") or "").upper().strip()
            strike = q.get("strike")
            option_type = str(q.get("option_type") or "").lower().strip()
            expiration = str(q.get("expiration") or "").strip()

            if not all([ticker, strike, option_type, expiration]):
                continue

            # Build unique key: ticker_strike_type_expiration
            # Example: VALE3_62.50_call_2024-03-15
            option_key = _build_option_key(ticker, strike, option_type, expiration)

            entry = {
                "ticker": ticker,
                "strike": _safe_float(strike),
                "option_type": option_type,
                "expiration": expiration,
                "mt5_symbol": q.get("mt5_symbol"),
                "bid": _safe_float(q.get("bid")),
                "ask": _safe_float(q.get("ask")),
                "last": _safe_float(q.get("last")),
                "volume": _safe_float(q.get("volume")),
                "source": "mt5",
                "ts": q.get("ts") or q.get("timestamp") or now_iso,
                "terminal_id": terminal_id,
                "account_number": account_number,
                "updated_at": now_iso,
            }

            _OPTIONS_QUOTES[option_key] = entry
            accepted += 1

    return accepted


def get_latest_option_quote(
    ticker: str,
    strike: float,
    expiration: str,
    option_type: str,
    ttl_seconds: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Get the latest option quote from cache (if within TTL).

    Args:
        ticker: Ticker symbol (e.g., "VALE3")
        strike: Strike price (e.g., 62.50)
        expiration: Expiration date ISO string (e.g., "2024-03-15")
        option_type: Option type ("call" or "put")
        ttl_seconds: TTL in seconds (default: QUOTE_TTL_SECONDS)

    Returns:
        Quote dict if found and not expired, None otherwise
    """
    ticker = (ticker or "").upper().strip()
    option_type = (option_type or "").lower().strip()
    expiration = (expiration or "").strip()

    if not all([ticker, strike, option_type, expiration]):
        return None

    option_key = _build_option_key(ticker, strike, option_type, expiration)
    ttl = int(ttl_seconds or QUOTE_TTL_SECONDS)
    now = datetime.now(timezone.utc)

    with _lock:
        entry = _OPTIONS_QUOTES.get(option_key)
        if not entry:
            return None

        ts = _parse_ts_iso(entry.get("ts"))
        age = (now - ts).total_seconds()

        if age > ttl:
            return None

        return dict(entry)


def get_all_option_quotes(max_age_seconds: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
    """
    Get all option quotes from cache (optionally filtered by age).

    Args:
        max_age_seconds: Maximum age in seconds (default: no filter)

    Returns:
        Dict mapping option_key -> quote
    """
    now = datetime.now(timezone.utc)
    max_age = max_age_seconds

    with _lock:
        if max_age is None:
            # Return all quotes
            return {k: dict(v) for k, v in _OPTIONS_QUOTES.items()}

        # Filter by age
        result = {}
        for key, entry in _OPTIONS_QUOTES.items():
            ts = _parse_ts_iso(entry.get("ts"))
            age = (now - ts).total_seconds()
            if age <= max_age:
                result[key] = dict(entry)

        return result


def _build_option_key(ticker: str, strike: float, option_type: str, expiration: str) -> str:
    """
    Build a unique key for an option.

    Args:
        ticker: Ticker symbol
        strike: Strike price
        option_type: "call" or "put"
        expiration: Expiration date string

    Returns:
        Unique key string
    """
    ticker = ticker.upper().strip()
    option_type = option_type.lower().strip()
    expiration = expiration.strip()
    return f"{ticker}_{strike}_{option_type}_{expiration}"


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None



# -----------------------------
# Commands queue (Fase 3)
# -----------------------------
from uuid import uuid4
from typing import List

# In-memory commands store
_COMMANDS: Dict[str, Dict[str, Any]] = {}


def enqueue_command(command: Dict[str, Any]) -> Dict[str, Any]:
    """Enqueue a command for MT5 terminal execution.

    Required fields in command:
      - type: e.g., "ROLL_POSITION", "OPEN_POSITION", "CLOSE_POSITION"
      - terminal_id
      - account_number
    """
    now_iso = _utcnow_iso()
    with _lock:
        cmd = dict(command)
        cmd_id = str(command.get("id") or uuid4())
        cmd["id"] = cmd_id
        cmd.setdefault("status", "PENDING")
        cmd.setdefault("created_at", now_iso)
        cmd["updated_at"] = now_iso
        _COMMANDS[cmd_id] = cmd
        return dict(cmd)


def get_pending_commands(
    terminal_id: Optional[str] = None,
    account_number: Optional[str] = None,
    max_count: int = 10,
) -> List[Dict[str, Any]]:
    """Return pending commands, filtered by terminal/account.

    Marks returned commands with dispatched_at (idempotent).
    """
    now_iso = _utcnow_iso()
    with _lock:
        items = [c for c in _COMMANDS.values() if c.get("status") in ("PENDING", "RETRY")]
        if terminal_id:
            items = [c for c in items if (c.get("terminal_id") or "") == terminal_id]
        if account_number:
            items = [c for c in items if (c.get("account_number") or "") == account_number]
        # Order by created_at
        def _ts(c: Dict[str, Any]):
            return _parse_ts_iso(c.get("created_at")).timestamp()
        items.sort(key=_ts)
        items = items[: max(1, int(max_count))]
        # Mark as dispatched
        for c in items:
            if not c.get("dispatched_at"):
                c["dispatched_at"] = now_iso
                c["status"] = c.get("status", "PENDING")
                c["updated_at"] = now_iso
        return [dict(c) for c in items]


def mark_commands_dispatched(ids: List[str]) -> None:
    now_iso = _utcnow_iso()
    with _lock:
        for cid in ids:
            c = _COMMANDS.get(cid)
            if not c:
                continue
            c["dispatched_at"] = c.get("dispatched_at") or now_iso
            c["updated_at"] = now_iso


def record_execution_report(report: Dict[str, Any]) -> None:
    """Record execution report from MT5 EA.

    Expected keys: command_id, status, order_id(optional), details(optional)
    """
    now_iso = _utcnow_iso()
    cid = str(report.get("command_id") or "").strip()
    with _lock:
        c = _COMMANDS.get(cid)
        if not c:
            # Create a placeholder for unknown command ids (so caller can audit)
            _COMMANDS[cid] = {
                "id": cid,
                "status": report.get("status") or "UNKNOWN",
                "last_report": report,
                "updated_at": now_iso,
            }
            return
        c["last_report"] = report
        status = str(report.get("status") or "").upper()
        if status in ("FILLED", "REJECTED", "CANCELLED"):
            c["status"] = status
            c["completed_at"] = now_iso
        else:
            # ACCEPTED / PARTIAL / etc.
            c["status"] = status or c.get("status")
        c["updated_at"] = now_iso



# ----- Helpers to fetch commands for UI -----
from typing import Optional as _Optional

def get_command_by_id(command_id: str) -> _Optional[Dict[str, Any]]:
    cid = str(command_id or "").strip()
    if not cid:
        return None
    with _lock:
        cmd = _COMMANDS.get(cid)
        return dict(cmd) if cmd else None


def list_commands(created_by: _Optional[str] = None, limit: int = 50) -> list[Dict[str, Any]]:
    """List commands (optionally filtered by creator), newest first.
    WARNING: in-memory only; for production use DB persistence.
    """
    with _lock:
        items = list(_COMMANDS.values())
        if created_by:
            uid = str(created_by).strip()
            items = [c for c in items if str(c.get("created_by") or "") == uid]
        # sort by created_at desc
        def _ts(c: Dict[str, Any]):
            try:
                ts = c.get("created_at")
                if isinstance(ts, str) and ts.endswith("Z"):
                    ts = ts[:-1] + "+00:00"
                return datetime.fromisoformat(ts).timestamp()
            except Exception:
                return 0.0
        items.sort(key=_ts, reverse=True)
        return [dict(c) for c in items[: max(1, int(limit))]]
