"""Roll preview and management routes."""

from sanic import Blueprint, response
from sanic.request import Request
from sanic_ext import openapi
from uuid import UUID
from app.services.roll_calculator import roll_calculator
from app.database.repositories.options import OptionsRepository
from app.database.repositories.accounts import AccountsRepository
from app.core.logger import logger
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.middleware.auth_middleware import require_auth


rolls_bp = Blueprint("rolls", url_prefix="/api/rolls")


@rolls_bp.post("/preview")
@openapi.tag("Rolls")
@openapi.summary("Get roll preview with suggestions")
@openapi.description("Get roll preview with suggestions for a position")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Roll preview with suggestions")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Position not found")
@openapi.response(422, description="Validation error")
@require_auth
async def get_roll_preview(request: Request):
    """
    Get roll preview with suggestions for a position.

    Request Body:
        {
            "option_position_id": "uuid",
            "market_data": {  // optional
                "current_price": 98.50,
                "bid": 98.45,
                "ask": 98.55
            }
        }

    Returns:
        200: Roll preview with suggestions
        401: Not authenticated
        403: Not authorized
        404: Position not found
        422: Validation error
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])

        data = request.json
        position_id = UUID(data.get("option_position_id"))
        market_data = data.get("market_data")

        # Check ownership
        position = await OptionsRepository.get_user_position(position_id, user_id)
        if not position:
            raise NotFoundError("Position", str(position_id))

        # If no market_data provided, try MT5 live quote
        if not market_data:
            try:
                from MT5.storage import get_latest_quote
                from app.database.repositories.assets import AssetsRepository
                ticker = position.get("ticker")
                if not ticker:
                    asset_id = UUID(position["asset_id"]) if not isinstance(position.get("asset_id"), UUID) else position["asset_id"]
                    asset = await AssetsRepository.get_by_id(asset_id, auth_user_id=user_id)
                    ticker = asset.get("ticker") if asset else None
                if ticker:
                    q = get_latest_quote(ticker)
                    if q:
                        bid = float(q.get("bid") or 0)
                        ask = float(q.get("ask") or 0)
                        last = float(q.get("last") or 0)
                        mid = (bid + ask) / 2 if bid and ask else (last or bid or ask)
                        if mid and mid > 0:
                            market_data = {
                                "ticker": ticker,
                                "current_price": round(mid, 2),
                                "bid": bid or None,
                                "ask": ask or None,
                                "volume": q.get("volume"),
                                "timestamp": q.get("ts") or q.get("timestamp"),
                            }
            except Exception:
                pass

        # Generate roll preview
        preview = await roll_calculator.get_roll_preview(
            position_id,
            market_data,
            auth_user_id=user_id
        )

        logger.info(
            "Roll preview generated",
            user_id=str(user_id),
            position_id=str(position_id),
            suggestions=len(preview["suggestions"])
        )

        return response.json(preview, status=200)

    except (NotFoundError, ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to generate roll preview", error=str(e))
        raise ValidationError(f"Failed to generate roll preview: {str(e)}")


@rolls_bp.get("/suggestions/<position_id:uuid>")
@openapi.tag("Rolls")
@openapi.summary("Get roll suggestions for position")
@openapi.description("Get roll suggestions for a position (simplified endpoint)")
@openapi.parameter("position_id", str, "path", description="Option position UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Roll suggestions")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized")
@openapi.response(404, description="Position not found")
@require_auth
async def get_roll_suggestions(request: Request, position_id: UUID):
    """
    Get roll suggestions for a position (simplified endpoint).

    Returns:
        200: Roll suggestions
        401: Not authenticated
        403: Not authorized
        404: Position not found
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])
        position_uuid = position_id if isinstance(position_id, UUID) else UUID(str(position_id))

        # Check ownership
        position = await OptionsRepository.get_user_position(position_uuid, user_id)
        if not position:
            raise NotFoundError("Position", position_id)

        # Try to use live MT5 quote for current_price if available
        market_data = None
        try:
            from MT5.storage import get_latest_quote
            from app.database.repositories.assets import AssetsRepository
            ticker = position.get("ticker")
            if not ticker:
                asset_id = UUID(position["asset_id"]) if not isinstance(position.get("asset_id"), UUID) else position["asset_id"]
                asset = await AssetsRepository.get_by_id(asset_id, auth_user_id=user_id)
                ticker = asset.get("ticker") if asset else None
            if ticker:
                q = get_latest_quote(ticker)
                if q:
                    bid = float(q.get("bid") or 0)
                    ask = float(q.get("ask") or 0)
                    last = float(q.get("last") or 0)
                    mid = (bid + ask) / 2 if bid and ask else (last or bid or ask)
                    if mid and mid > 0:
                        market_data = {
                            "ticker": ticker,
                            "current_price": round(mid, 2),
                            "bid": bid or None,
                            "ask": ask or None,
                            "volume": q.get("volume"),
                            "timestamp": q.get("ts") or q.get("timestamp"),
                        }
        except Exception:
            market_data = None

        # Generate preview
        preview = await roll_calculator.get_roll_preview(position_uuid, market_data, auth_user_id=user_id)

        # Return only suggestions
        return response.json(
            {
                "position_id": str(position_uuid),
                "suggestions": preview["suggestions"],
                "current_metrics": {
                    "dte": preview["current_position"].get("dte"),
                    "otm_pct": preview["current_position"].get("otm_pct"),
                    "current_price": preview["current_position"].get("current_price")
                }
            },
            status=200
        )

    except (NotFoundError, ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get roll suggestions", error=str(e))
        raise ValidationError(f"Failed to get roll suggestions: {str(e)}")


@rolls_bp.get("/analysis/<account_id:uuid>")
@openapi.tag("Rolls")
@openapi.summary("Get account roll analysis")
@openapi.description("Get roll analysis for all open positions in an account")
@openapi.parameter("account_id", str, "path", description="Account UUID")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Roll analysis for account")
@openapi.response(401, description="Not authenticated")
@openapi.response(403, description="Not authorized to access this account")
@require_auth
async def get_account_roll_analysis(request: Request, account_id: UUID):
    """
    Get roll analysis for all open positions in an account.

    Returns:
        200: Roll analysis for account
        401: Not authenticated
        403: Not authorized
    """
    try:
        user = request.ctx.user
        user_id = UUID(user["id"])
        account_uuid = account_id if isinstance(account_id, UUID) else UUID(str(account_id))

        # Check ownership
        if not await AccountsRepository.user_owns_account(account_uuid, user_id):
            raise AuthorizationError("Not authorized to access this account")

        # Get all open positions
        open_positions = await OptionsRepository.get_open_positions(account_uuid, auth_user_id=user_id)

        analysis = []

        for position in open_positions:
            try:
                # Generate preview for each position
                preview = await roll_calculator.get_roll_preview(
                    UUID(position["id"]),
                    auth_user_id=user_id
                )

                # Get best suggestion
                best_suggestion = preview["suggestions"][0] if preview["suggestions"] else None

                analysis.append({
                    "position_id": position["id"],
                    "ticker": position.get("ticker"),
                    "strike": position.get("strike"),
                    "expiration": position.get("expiration"),
                    "side": position.get("side"),
                    "current_metrics": {
                        "dte": preview["current_position"].get("dte"),
                        "otm_pct": preview["current_position"].get("otm_pct"),
                        "pnl": preview["current_position"].get("pnl")
                    },
                    "best_suggestion": best_suggestion,
                    "total_suggestions": len(preview["suggestions"])
                })

            except Exception as e:
                logger.warning(
                    "Failed to analyze position",
                    position_id=position["id"],
                    error=str(e)
                )
                continue

        logger.info(
            "Account roll analysis completed",
            user_id=str(user_id),
            account_id=str(account_id),
            positions_analyzed=len(analysis)
        )

        return response.json(
            {
                "account_id": str(account_uuid),
                "positions": analysis,
                "total_positions": len(analysis)
            },
            status=200
        )

    except (NotFoundError, ValidationError, AuthorizationError):
        raise
    except Exception as e:
        logger.error("Failed to get account roll analysis", error=str(e))
        raise ValidationError(f"Failed to get account roll analysis: {str(e)}")



@rolls_bp.post("/mt5/execute")
@openapi.tag("Rolls")
@openapi.summary("Enfileira rolagem automática via MetaTrader 5")
@openapi.secured("BearerAuth")
@require_auth
async def execute_roll_mt5(request: Request):
    """
    Enfileira uma rolagem (fechar opção atual e abrir nova) para execução no MT5.

    Body esperado:
    {
      "option_position_id": "<uuid>",
      "suggestion": { "strike": 0.0, "expiration": "YYYY-MM-DD" },
      "min_net_credit": 0.0
    }
    """
    from uuid import UUID as _UUID, uuid4 as _uuid4
    from datetime import datetime as _dt
    from MT5.storage import enqueue_command, get_all_heartbeats
    from app.database.repositories.assets import AssetsRepository

    user = request.ctx.user
    user_id = UUID(user["id"])

    if not getattr(__import__('app.config', fromlist=['settings']).config.settings, 'MT5_BRIDGE_ENABLED', False):
        return response.json({"error": "mt5_bridge_disabled"}, status=403)

    data = request.json or {}
    try:
        position_id = _UUID(str(data.get("option_position_id")))
        suggestion = data.get("suggestion") or {}
        target_strike = float(suggestion.get("strike"))
        target_expiration = str(suggestion.get("expiration"))
        min_net_credit = data.get("min_net_credit")
    except Exception:
        raise ValidationError("Payload inválido para execução de rolagem")

    # Carrega posição e valida dono
    position = await OptionsRepository.get_user_position(position_id, user_id)
    if not position:
        raise NotFoundError("Position", str(position_id))

    account_id = _UUID(position["account_id"]) if not isinstance(position["account_id"], UUID) else position["account_id"]
    asset_id = _UUID(position["asset_id"]) if not isinstance(position["asset_id"], UUID) else position["asset_id"]

    account = await AccountsRepository.get_by_id(account_id, auth_user_id=user_id)
    if not account:
        raise AuthorizationError("Conta não encontrada ou sem permissão")

    asset = await AssetsRepository.get_by_id(asset_id, auth_user_id=user_id)
    ticker = asset.get("ticker") if asset else None
    if not ticker:
        raise ValidationError("Ticker do ativo não encontrado para a posição")

    # Encontra terminal ativo para a conta via heartbeat recente
    heartbeats = get_all_heartbeats(max_age_seconds=120)
    terminal_id = None
    for hb in heartbeats.values():
        if str(hb.get("account_number")) == str(account.get("account_number")):
            terminal_id = hb.get("terminal_id")
            break
    if not terminal_id:
        return response.json({"error": "mt5_terminal_not_connected"}, status=412)

    side_upper = str(position.get("side") or "").upper()
    side_lower = "call" if side_upper == "CALL" else "put"
    qty = int(position.get("quantity") or 0)

    # Monta comando
    cmd = {
        "id": str(_uuid4()),
        "type": "ROLL_POSITION",
        "terminal_id": terminal_id,
        "account_number": account.get("account_number"),
        "position_id": str(position_id),
        "timestamp": _dt.utcnow().isoformat() + "Z",
        "close_leg": {
            "ticker": ticker,
            "strike": float(position.get("strike")),
            "option_type": side_lower,
            "expiration": str(position.get("expiration")),
            "quantity": qty,
            "action": "BUY_TO_CLOSE",
        },
        "open_leg": {
            "ticker": ticker,
            "strike": float(target_strike),
            "option_type": side_lower,
            "expiration": target_expiration,
            "quantity": qty,
            "action": "SELL_TO_OPEN",
        },
        "constraints": {
            "min_net_credit": min_net_credit,
            "time_in_force": data.get("time_in_force") or "DAY",
        },
        "status": "PENDING",
        "created_by": str(user_id),
    }

    saved = enqueue_command(cmd)
    logger.info("rolls.mt5.enqueue", command_id=saved["id"], terminal_id=terminal_id, position_id=str(position_id))

    return response.json({"command": saved}, status=201)


@rolls_bp.get("/mt5/command/<command_id>")
@openapi.tag("Rolls")
@openapi.summary("Obter status de execucao MT5 enfileirada (apenas do proprio usuario)")
@openapi.secured("BearerAuth")
@require_auth
async def get_roll_mt5_command_status(request: Request, command_id: str):
    from uuid import UUID as _UUID
    try:
        user = request.ctx.user
        user_id = _UUID(user["id"])  # valida UUID
    except Exception:
        return response.json({"error": "unauthorized"}, status=401)

    try:
        from MT5.storage import get_command_by_id as _get_cmd
    except Exception as e:
        return response.json({"error": "bridge_not_available", "details": str(e)}, status=503)

    cmd = _get_cmd(command_id)
    if not cmd:
        return response.json({"error": "not_found"}, status=404)

    if str(cmd.get("created_by") or "") != str(user_id):
        # Nao revelar existencia de comandos de outros usuarios
        return response.json({"error": "not_found"}, status=404)

    # Opcional: esconder campos internos
    sanitized = dict(cmd)
    return response.json({"command": sanitized}, status=200)


@rolls_bp.get("/mt5/commands")
@openapi.tag("Rolls")
@openapi.summary("Listar comandos MT5 do usuario autenticado (mais recentes primeiro)")
@openapi.secured("BearerAuth")
@require_auth
async def list_roll_mt5_commands(request: Request):
    try:
        from MT5.storage import list_commands as _list_cmds
    except Exception as e:
        return response.json({"error": "bridge_not_available", "details": str(e)}, status=503)

    user = request.ctx.user
    user_id = str(user.get("id") or "").strip()
    if not user_id:
        return response.json({"error": "unauthorized"}, status=401)

    try:
        limit = int(request.args.get("limit", 50))
    except Exception:
        limit = 50

    cmds = _list_cmds(created_by=user_id, limit=limit)
    return response.json({"commands": cmds, "count": len(cmds)}, status=200)


