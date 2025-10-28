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
from .storage import upsert_heartbeat, upsert_quotes

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
    payload: Dict[str, Any] = request.json or {}
    accepted = upsert_quotes(payload)
    logger.info("mt5.quotes", count=accepted)
    return response.json({"accepted": int(accepted)}, status=202)


@mt5_bridge_bp.get("/commands")
@openapi.tag("MT5 Bridge")
@openapi.summary("Lista comandos pendentes para o terminal/conta")
async def commands(request: Request):
    deny = _require_enabled_and_auth(request)
    if deny:
        return deny
    # Fase 1: fila vazia
    return response.json({"commands": []}, status=200)


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

