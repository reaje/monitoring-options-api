"""Sanic blueprint para o MT5 Bridge (EA MQL5).

Rotas v1:
- POST /api/mt5/heartbeat
- POST /api/mt5/quotes
- GET  /api/mt5/commands
- POST /api/mt5/execution_report

Observação: blueprint já pode ser registrado em app/main.py.
"""
from __future__ import annotations

from sanic import Blueprint, response
from sanic.request import Request
from sanic_ext import openapi
from app.config import settings
from typing import Any, Dict

from app.core.logger import logger
from .storage import upsert_heartbeat, upsert_quotes, upsert_option_quotes
from datetime import datetime, timezone
from .storage import get_all_heartbeats, get_all_quotes, QUOTE_TTL_SECONDS

from .symbol_mapper import get_mapper

mt5_bridge_bp = Blueprint("mt5_bridge", url_prefix="/api/mt5")

# Segurança básica por token (via settings/.env)
BRIDGE_ENABLED = bool(settings.MT5_BRIDGE_ENABLED)
BRIDGE_TOKEN = settings.MT5_BRIDGE_TOKEN or ""
ALLOWED_IPS = set(ip.strip() for ip in (settings.MT5_BRIDGE_ALLOWED_IPS or "").split(",") if ip.strip())


def _authorized(request: Request) -> bool:
    # Token
    auth = request.headers.get("Authorization", "")
    ok_token = BRIDGE_TOKEN and auth.startswith("Bearer ") and auth.split(" ", 1)[1] == BRIDGE_TOKEN
    if not ok_token:
        return False
    # Allowlist IP (opcional)
    if ALLOWED_IPS:
        peer_ip = request.remote_addr or ""
        if peer_ip not in ALLOWED_IPS:
            logger.warning("MT5 bridge request from non-allowed IP", ip=peer_ip)
            return False
    return True


def _require_enabled_and_auth(request: Request):
    if not BRIDGE_ENABLED:
        return response.json({"error": "mt5 bridge disabled"}, status=403)
    if not _authorized(request):
        return response.json({"error": "unauthorized"}, status=401)
    return None


@mt5_bridge_bp.post("/heartbeat")
@openapi.tag("MT5 Bridge")
@openapi.summary("Recebe heartbeat do terminal MT5")
async def heartbeat(request: Request):
    deny = _require_enabled_and_auth(request)
    if deny:
        return deny

    payload: Dict[str, Any] = request.json or {}
    upsert_heartbeat(payload)
    logger.info(
        "mt5.heartbeat",
        **{k: str(v) for k, v in payload.items() if k in ("terminal_id", "account_number", "broker", "build")},
    )
    return response.json({"status": "ok"}, status=200)


@mt5_bridge_bp.post("/quotes")
@openapi.tag("MT5 Bridge")
@openapi.summary("Recebe snapshots de cotações do EA MQL5")
async def quotes(request: Request):
    deny = _require_enabled_and_auth(request)
    if deny:
        return deny

    # Parse JSON payload
    try:
        payload: Dict[str, Any] = request.json or {}
    except Exception as e:
        # JSON parse error
        logger.error("mt5.quotes.json_parse_error", error=str(e), error_type=type(e).__name__)
        return response.json({
            "error": "invalid_json",
            "details": str(e)
        }, status=400)

    # Process quotes
    try:
        accepted = upsert_quotes(payload)
        logger.info("mt5.quotes", count=accepted)
        return response.json({"accepted": int(accepted)}, status=202)
    except Exception as e:
        logger.error("mt5.quotes.processing_error", error=str(e))
        return response.json({"error": "processing_error", "details": str(e)}, status=500)


@mt5_bridge_bp.get("/commands")
@openapi.tag("MT5 Bridge")
@openapi.summary("Lista comandos pendentes para o terminal/conta")
async def commands(request: Request):
    deny = _require_enabled_and_auth(request)
    if deny:
        return deny
    # Fase 1: fila vazia
    return response.json({"commands": []}, status=200)


@mt5_bridge_bp.post("/option_quotes")
@openapi.tag("MT5 Bridge")
@openapi.summary("Recebe cotações de opções do MT5 com mapeamento automático")
async def option_quotes(request: Request):
    deny = _require_enabled_and_auth(request)
    if deny:
        return deny

    # Parse JSON payload
    try:
        payload: Dict[str, Any] = request.json or {}
    except Exception as e:
        logger.error("mt5.option_quotes.json_parse_error", error=str(e), error_type=type(e).__name__)
        return response.json({
            "error": "invalid_json",
            "details": str(e)
        }, status=400)

    # Process option quotes with symbol mapping
    try:
        mapper = get_mapper()
        option_quotes_raw = payload.get("option_quotes") or []
        mapped_quotes = []
        mapping_errors = []

        for idx, quote in enumerate(option_quotes_raw):
            mt5_symbol = quote.get("mt5_symbol")

            if not mt5_symbol:
                mapping_errors.append({"index": idx, "error": "missing_mt5_symbol"})
                continue

            try:
                # Decode MT5 symbol to backend format
                decoded = mapper.decode_mt5_symbol(mt5_symbol)

                # Add mapped information to quote
                quote.update({
                    "ticker": decoded["ticker"],
                    "strike": decoded["strike"],
                    "option_type": decoded["option_type"],
                    "expiration": decoded["expiration_date"],
                })

                mapped_quotes.append(quote)

            except ValueError as e:
                # Mapping failed
                logger.warning(
                    "mt5.option_quotes.mapping_failed",
                    mt5_symbol=mt5_symbol,
                    error=str(e)
                )
                mapping_errors.append({
                    "index": idx,
                    "mt5_symbol": mt5_symbol,
                    "error": str(e)
                })

        # Store mapped quotes
        payload_with_mapped = {
            **payload,
            "option_quotes": mapped_quotes
        }

        accepted = upsert_option_quotes(payload_with_mapped)

        logger.info(
            "mt5.option_quotes",
            count=accepted,
            total_received=len(option_quotes_raw),
            mapping_errors=len(mapping_errors)
        )

        return response.json({
            "accepted": accepted,
            "total": len(option_quotes_raw),
            "mapping_errors": mapping_errors if mapping_errors else None
        }, status=202)
    except Exception as e:
        logger.error(
            "mt5.option_quotes.processing_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        return response.json({
            "error": "processing_error",
            "details": str(e),
        }, status=500)

@mt5_bridge_bp.get("/health")
@openapi.tag("MT5 Bridge")
@openapi.summary("Saúde do bridge MT5 (heartbeats e cotações)")
async def mt5_health(request: Request):
    deny = _require_enabled_and_auth(request)
    if deny:
        return deny

    now = datetime.now(timezone.utc)

    # Heartbeats
    heartbeats = get_all_heartbeats()
    latest_hb = None
    latest_hb_age = None
    if heartbeats:
        # Seleciona o mais recente por updated_at/ts
        def hb_ts(hb):
            ts = hb.get("updated_at") or hb.get("ts")
            try:
                if isinstance(ts, str) and ts.endswith("Z"):
                    ts = ts[:-1] + "+00:00"
                return datetime.fromisoformat(ts).astimezone(timezone.utc)
            except Exception:
                return now
        latest_hb = max(heartbeats.values(), key=hb_ts)
        latest_hb_ts = hb_ts(latest_hb)
        latest_hb_age = (now - latest_hb_ts).total_seconds()

    # Quotes (subjacentes)
    quotes = get_all_quotes()
    fresh_quotes = 0
    stale_quotes = 0
    quotes_summary = {}
    for sym, q in quotes.items():
        try:
            ts = q.get("ts")
            if isinstance(ts, str) and ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            qts = datetime.fromisoformat(ts).astimezone(timezone.utc)
        except Exception:
            qts = now
        age = (now - qts).total_seconds()
        is_fresh = age <= float(QUOTE_TTL_SECONDS)
        fresh_quotes += 1 if is_fresh else 0
        stale_quotes += 0 if is_fresh else 1
        # Amostra compacta por símbolo
        quotes_summary[sym] = {
            "last": q.get("last"),
            "bid": q.get("bid"),
            "ask": q.get("ask"),
            "ts": q.get("ts"),
            "age_seconds": age,
            "is_fresh": is_fresh,
        }

    # Status: ok, degraded, unhealthy
    hb_recent = latest_hb_age is not None and latest_hb_age <= 60
    has_fresh_quotes = fresh_quotes > 0
    if hb_recent and has_fresh_quotes:
        status = "ok"
    elif hb_recent or has_fresh_quotes or stale_quotes > 0:
        status = "degraded"
    else:
        status = "unhealthy"

    result = {
        "status": status,
        "bridge_enabled": BRIDGE_ENABLED,
        "quote_ttl_seconds": QUOTE_TTL_SECONDS,
        "heartbeat": {
            "terminals": len(heartbeats),
            "latest": latest_hb,
            "latest_age_seconds": latest_hb_age,
        },
        "quotes": {
            "symbols_total": len(quotes),
            "fresh": fresh_quotes,
            "stale": stale_quotes,
            "sample": dict(list(quotes_summary.items())[:10]),
        },
        "timestamp": now.isoformat().replace("+00:00", "Z"),
    }

    return response.json(result, status=200)




@mt5_bridge_bp.post("/execution_report")
@openapi.tag("MT5 Bridge")
@openapi.summary("Recebe relatório de execução de ordens")
async def execution_report(request: Request):
    deny = _require_enabled_and_auth(request)
    if deny:
        return deny
    payload: Dict[str, Any] = request.json or {}
    logger.info(
        "mt5.execution_report",
        **{k: str(v) for k, v in payload.items() if k in ("command_id", "status", "order_id")},
    )
    # Fase 1: apenas loga
    return response.json({"status": "ok"}, status=200)

