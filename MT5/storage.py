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


def get_latest_option_quote(
    ticker: str,
    strike: float,
    expiration: str,
    option_type: str,
    ttl_seconds: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Placeholder: Fase 1 não usa cotações de opções via MT5.
    Retorna None para sempre delegar ao fallback provider.
    """
    return None


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None

