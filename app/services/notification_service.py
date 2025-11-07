"""Notification service for sending alerts via multiple channels."""

from typing import Dict, Any, List, Optional
from uuid import UUID
import asyncio
from app.services.communications_client import comm_client
from app.database.repositories.alerts import AlertQueueRepository
from app.database.repositories.alert_logs import AlertLogsRepository
from app.database.repositories.accounts import AccountsRepository
from app.database.repositories.options import OptionsRepository
from app.database.repositories.assets import AssetsRepository
from app.core.logger import logger
from app.config import settings
from app.services.market_data import get_market_data_provider
from app.services.market_data.brapi_provider import brapi_provider


class NotificationService:
    """Service for processing and sending notifications."""

    def __init__(self):
        """Initialize notification service."""
        self.comm_client = comm_client
        self.max_retries = getattr(settings, "MAX_NOTIFICATION_RETRIES", 3)
        self.retry_delay = 5  # seconds

    async def process_alert(self, alert: Dict[str, Any]) -> bool:
        """
        Process a single alert and send notifications.

        Args:
            alert: Alert dict from alert_queue

        Returns:
            True if all notifications sent successfully
        """
        alert_id = UUID(alert["id"])
        account_id = UUID(alert["account_id"])

        try:
            # Mark as processing
            await AlertQueueRepository.mark_as_processing(alert_id)

            # Get account details
            account = await AccountsRepository.get_by_id(account_id)
            if not account:
                logger.error("Account not found", alert_id=str(alert_id))
                await AlertQueueRepository.mark_as_failed(alert_id, "Account not found")
                return False

            # Get notification channels and target from account or alert payload
            # Normalizar payload (alguns registros antigos podem ter JSON serializado como string)
            import json as _json
            _payload = alert.get("payload") or {}
            if isinstance(_payload, str):
                try:
                    _payload = _json.loads(_payload)
                except Exception:
                    _payload = {}
            alert["payload"] = _payload

            # Normalizar canais para lista
            _channels = _payload.get("channels") or []
            if isinstance(_channels, str):
                try:
                    parsed = _json.loads(_channels)
                    _channels = parsed if isinstance(parsed, list) else [_channels]
                except Exception:
                    _channels = [_channels]
            elif not isinstance(_channels, list):
                _channels = []
            channels = list(dict.fromkeys(_channels + ["whatsapp", "sms"]))

            phone = account.get("phone") or _payload.get("phone")
            email = account.get("email")

            # Enriquecer payload legado/incompleto on-the-fly (e persistir no banco)
            try:
                payload = alert.get("payload") or {}
                def _is_missing(v):
                    return v is None or (isinstance(v, str) and (v.strip() == "" or v.strip().upper() == "N/A"))
                if alert.get("reason") == "roll_trigger":
                    missing_core = any(_is_missing(payload.get(k)) for k in ["ticker", "side", "strike", "expiration", "dte"])
                    if missing_core:
                        pos_id = alert.get("option_position_id")
                        if pos_id:
                            from uuid import UUID as _UUID
                            pos = await OptionsRepository.get_by_id(_UUID(str(pos_id)))
                            patch: Dict[str, Any] = {}
                            if pos:
                                # Buscar ticker via asset
                                ticker: Optional[str] = payload.get("ticker")
                                if not ticker and pos.get("asset_id"):
                                    asset = await AssetsRepository.get_by_id(_UUID(str(pos.get("asset_id"))))
                                    if asset:
                                        ticker = asset.get("ticker")
                                patch["ticker"] = ticker or pos.get("ticker")
                                patch["side"] = payload.get("side") or pos.get("side")
                                patch["strike"] = payload.get("strike") or pos.get("strike")
                                patch["expiration"] = payload.get("expiration") or pos.get("expiration")
                                patch["quantity"] = payload.get("quantity") or pos.get("quantity")
                                patch["avg_premium"] = payload.get("avg_premium") or pos.get("avg_premium")
                                # Calcular DTE se necessario
                                if _is_missing(payload.get("dte")) and patch.get("expiration"):
                                    from datetime import date as _date, datetime as _dt
                                    exp = patch.get("expiration")
                                    if isinstance(exp, str):
                                        try:
                                            exp_d = _dt.fromisoformat(exp).date()
                                        except Exception:
                                            exp_d = None
                                    elif isinstance(exp, _dt):
                                        exp_d = exp.date()
                                    else:
                                        exp_d = exp
                                    if exp_d is not None:
                                        patch["dte"] = (exp_d - _date.today()).days
                                patch["payload_version"] = 2
                                # Persistir merge para atualizar UI
                                await AlertQueueRepository.merge_payload(alert_id, {k: v for k, v in patch.items() if v is not None})
                                payload.update({k: v for k, v in patch.items() if v is not None})
                                alert["payload"] = payload

                # Enriquecimento de mercado (preco/premio/greeks/moneyness)
                try:
                    payload = alert.get("payload") or {}
                    ticker = (payload.get("ticker") or "").upper()
                    side = (payload.get("side") or "").upper()
                    strike = payload.get("strike")
                    expiration = payload.get("expiration")

                    # Calcular DTE se nao informado
                    try:
                        if payload.get("dte") in (None, "N/A") and expiration and isinstance(expiration, str) and len(expiration) >= 10:
                            from datetime import date as _date
                            exp_str = expiration[:10]
                            dte = (_date.fromisoformat(exp_str) - _date.today()).days
                            if dte < 0:
                                dte = 0
                            await AlertQueueRepository.merge_payload(alert_id, {"dte": dte})
                            payload["dte"] = dte
                    except Exception:
                        pass

                    # Apenas se tivermos o minimo necessario
                    if ticker and strike and expiration and side in ("CALL", "PUT"):
                        provider = get_market_data_provider()
                        price_val = None
                        try:
                            q = await provider.get_quote(ticker)
                            price_val = q.get("current_price")
                        except Exception:
                            # Fallback brapi para notificacao (nao bloqueante)
                            try:
                                q = await brapi_provider.get_quote(ticker)
                                price_val = q.get("current_price")
                            except Exception:
                                price_val = None

                        premium_val = None
                        delta_val = payload.get("delta")
                        try:
                            opt_type = "call" if side == "CALL" else "put"
                            oq = await provider.get_option_quote(ticker, float(strike), str(expiration), opt_type)
                            premium_val = oq.get("premium")
                            greeks = oq.get("greeks") or {}
                            if delta_val is None and greeks.get("delta") is not None:
                                delta_val = greeks.get("delta")
                        except NotImplementedError:
                            try:
                                oq = await brapi_provider.get_option_quote(ticker, float(strike), str(expiration), opt_type)
                                premium_val = oq.get("premium")
                                greeks = oq.get("greeks") or {}
                                if delta_val is None and greeks.get("delta") is not None:
                                    delta_val = greeks.get("delta")
                            except Exception:
                                pass
                        except Exception:
                            pass

                        # Calcular moneyness/otm_pct se possivel
                        mny = payload.get("moneyness")
                        otm_pct = payload.get("otm_pct")
                        if mny is None or otm_pct is None:
                            try:
                                if isinstance(price_val, (int, float)) and isinstance(strike, (int, float)):
                                    if side == "CALL":
                                        mny = "ITM" if price_val > strike else "OTM"
                                        otm_pct = max((strike - float(price_val)) / float(price_val), 0.0)
                                    else:  # PUT
                                        mny = "ITM" if price_val < strike else "OTM"
                                        otm_pct = max((float(price_val) - strike) / float(price_val), 0.0)
                            except Exception:
                                pass

                        # Calcular PnL de premio (aproximado)
                        pnl_premium = payload.get("pnl_premium")
                        avg_premium = payload.get("avg_premium")
                        if pnl_premium is None and isinstance(premium_val, (int, float)) and isinstance(avg_premium, (int, float)):
                            try:
                                pnl_premium = float(premium_val) - float(avg_premium)
                            except Exception:
                                pnl_premium = None

                        patch2 = {}
                        if price_val is not None:
                            patch2["price"] = price_val
                        if premium_val is not None:
                            patch2["premium"] = premium_val
                        if delta_val is not None:
                            patch2["delta"] = float(delta_val)
                        if mny is not None:
                            patch2["moneyness"] = mny
                        if otm_pct is not None:
                            patch2["otm_pct"] = float(otm_pct)
                        if pnl_premium is not None:
                            patch2["pnl_premium"] = float(pnl_premium)

                        if patch2:
                            await AlertQueueRepository.merge_payload(alert_id, patch2)
                            payload.update(patch2)
                            alert["payload"] = payload
                except Exception as _e:
                    logger.warning("Falha ao enriquecer dados de mercado", alert_id=str(alert_id), error=str(_e))
            except Exception as e:
                logger.warning("Falha ao enriquecer payload legado", alert_id=str(alert_id), error=str(e))

            # Build message
            message = self._build_message(alert)

            # Send notifications to each channel
            all_success = True
            for channel in channels:
                success = await self._send_to_channel(
                    alert_id,
                    channel,
                    phone,
                    email,
                    message
                )
                if not success:
                    all_success = False

            # Update alert status
            if all_success:
                await AlertQueueRepository.mark_as_sent(alert_id)
                logger.info("Alert processed successfully", alert_id=str(alert_id))
            else:
                await AlertQueueRepository.mark_as_failed(
                    alert_id,
                    "One or more channels failed"
                )

            return all_success

        except Exception as e:
            logger.error(
                "Failed to process alert",
                alert_id=str(alert_id),
                error=str(e)
            )
            await AlertQueueRepository.mark_as_failed(alert_id, str(e))
            return False

    async def _send_to_channel(
        self,
        alert_id: UUID,
        channel: str,
        phone: Optional[str],
        email: Optional[str],
        message: str
    ) -> bool:
        """
        Send notification to a specific channel with retry logic.

        Args:
            alert_id: Alert UUID
            channel: Channel name (whatsapp, sms, email)
            phone: Target phone number
            email: Target email
            message: Message content

        Returns:
            True if sent successfully
        """
        for attempt in range(self.max_retries):
            try:
                if channel == "whatsapp":
                    if not phone:
                        logger.warning("No phone number for WhatsApp", alert_id=str(alert_id))
                        return False

                    result = await self.comm_client.send_whatsapp(phone, message)
                    await AlertLogsRepository.create_log(
                        queue_id=alert_id,
                        channel="whatsapp",
                        target=phone,
                        message=message,
                        status="success",
                        provider_msg_id=(result.get("message_id") or result.get("id") or result.get("externalId") or result.get("messageId"))
                    )
                    return True

                elif channel == "sms":
                    if not phone:
                        logger.warning("No phone number for SMS", alert_id=str(alert_id))
                        return False

                    result = await self.comm_client.send_sms(phone, message)
                    await AlertLogsRepository.create_log(
                        queue_id=alert_id,
                        channel="sms",
                        target=phone,
                        message=message,
                        status="success",
                        provider_msg_id=(result.get("message_id") or result.get("id") or result.get("externalId") or result.get("messageId"))
                    )
                    return True

                elif channel == "email":
                    if not email:
                        logger.warning("No email address", alert_id=str(alert_id))
                        return False

                    result = await self.comm_client.send_email(
                        email=email,
                        subject="Alerta - Monitoring Options",
                        message=message
                    )
                    await AlertLogsRepository.create_log(
                        queue_id=alert_id,
                        channel="email",
                        target=email,
                        message=message,
                        status="success",
                        provider_msg_id=(result.get("message_id") or result.get("id") or result.get("externalId") or result.get("messageId"))
                    )
                    return True

                else:
                    logger.warning("Unknown channel", channel=channel)
                    return False

            except Exception as e:
                logger.warning(
                    "Failed to send notification, retrying",
                    alert_id=str(alert_id),
                    channel=channel,
                    attempt=attempt + 1,
                    error=str(e)
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    # Final attempt failed, log it
                    target = phone if channel in ["whatsapp", "sms"] else email
                    await AlertLogsRepository.create_log(
                        queue_id=alert_id,
                        channel=channel,
                        target=target or "unknown",
                        message=message,
                        status="failed"
                    )
                    return False

        return False

    def _build_message(self, alert: Dict[str, Any]) -> str:
        """
        Build notification message from alert data.

        Args:
            alert: Alert dict

        Returns:
            Formatted message string
        """
        reason = alert.get("reason", "notification")
        payload = alert.get("payload", {})

        # Check if custom message exists
        if "message" in payload:
            return payload["message"]

        # Build message based on reason
        if reason == "roll_trigger":
            return self._build_roll_trigger_message_v2(payload)
        elif reason == "expiration_warning":
            return self._build_expiration_warning_message_v2(payload)
        elif reason == "delta_threshold":
            return self._build_delta_threshold_message_v2(payload)
        else:
            return f"Alerta: {reason}"

    # Versao V2 com texto corrigido (sem acentuacao) e formato compacto para canais externos
    def _build_roll_trigger_message_v2(self, payload: Dict[str, Any]) -> str:
        """Mensagem de rolagem com contexto acionavel (compacta para WhatsApp/SMS)."""
        ticker = payload.get("ticker", "N/A")
        side = str(payload.get("side", "")).upper() or "N/A"
        strike = payload.get("strike")
        expiration = payload.get("expiration")
        dte = payload.get("dte")
        price = payload.get("price")
        premium = payload.get("premium")
        avg_premium = payload.get("avg_premium")
        pnl_premium = payload.get("pnl_premium")
        quantity = payload.get("quantity")
        mny = payload.get("moneyness")
        otm_pct = payload.get("otm_pct")
        delta = payload.get("delta")
        hint = payload.get("action_hint")

        # Helpers de formatacao
        def fmt_money(v):
            return f"R$ {float(v):.2f}" if isinstance(v, (int, float)) else "N/A"
        def fmt_pct(v):
            return f"{float(v)*100:.2f}%" if isinstance(v, (int, float)) else "N/A"
        def fmt_num(v):
            return f"{float(v):.2f}" if isinstance(v, (int, float)) else "N/A"

        head = f"Rolagem: {ticker} {side} {fmt_num(strike)} | Venc: {expiration} (DTE {dte})"
        line2 = f"Subjacente: {fmt_money(price)} | Premio: {fmt_money(premium)}"
        if avg_premium is not None or pnl_premium is not None:
            line2 += f" (media {fmt_money(avg_premium)}"
            if pnl_premium is not None:
                line2 += f", PnL {fmt_money(pnl_premium)}"
            line2 += ")"

        line3 = f"Status: {mny or 'N/A'}"
        if otm_pct is not None:
            line3 += f" ({fmt_pct(otm_pct)})"
        if delta is not None:
            line3 += f" | Delta: {fmt_num(delta)}"

        line4 = hint or "Sugestao: rolar mantendo faixa OTM alvo (ver detalhes no app)."

        return f"{head}\n{line2}\n{line3}\n{line4}"

    def _build_expiration_warning_message_v2(self, payload: Dict[str, Any]) -> str:
        """Mensagem de vencimento proximo com sugestao objetiva."""
        ticker = payload.get("ticker", "N/A")
        side = str(payload.get("side", "")).upper() or "N/A"
        strike = payload.get("strike")
        days = payload.get("days_to_expiration")
        expiration = payload.get("expiration")
        qty = payload.get("quantity")

        # Calcular dias ate o vencimento se nao vier no payload
        if days in (None, "N/A") and expiration:
            try:
                from datetime import date as _date
                exp_str = expiration[:10] if isinstance(expiration, str) else None
                if exp_str:
                    dte = (_date.fromisoformat(exp_str) - _date.today()).days
                    days = max(dte, 0)
            except Exception:
                days = "N/A"

        def fmt_num(v):
            return f"{float(v):.2f}" if isinstance(v, (int, float)) else "N/A"

        days_display = days if isinstance(days, int) else "N/A"
        unit = "dia" if days_display == 1 else "dias"
        parts = [ticker]
        if side and side != "N/A":
            parts.append(side)
        if isinstance(strike, (int, float)):
            parts.append(fmt_num(strike))
        asset_str = " ".join(parts)
        head = f"Aviso: Vencimento em {days_display} {unit}: {asset_str}"
        line2 = f"Venc: {expiration} | Qtd: {qty or 'N/A'}"
        line3 = "Sugestao: avaliar rolagem hoje para evitar exercicio indesejado."
        return f"{head}\n{line2}\n{line3}"

    def _build_delta_threshold_message_v2(self, payload: Dict[str, Any]) -> str:
        """Mensagem de delta com contexto do strike."""
        ticker = payload.get("ticker", "N/A")
        side = str(payload.get("side", "")).upper() or "N/A"
        strike = payload.get("strike")
        delta = payload.get("delta")
        threshold = payload.get("threshold")

        def fmt_num(v):
            return f"{float(v):.2f}" if isinstance(v, (int, float)) else "N/A"

        head = "Delta atingiu limite"
        line2 = f"{ticker} {side} {fmt_num(strike)} | Delta: {fmt_num(delta)} (limite {fmt_num(threshold)})"
        line3 = "A opcao esta se aproximando do strike (risco de exercicio)."
        return f"{head}\n{line2}\n{line3}"

    async def process_pending_alerts(self, limit: int = 100) -> Dict[str, int]:
        """
        Process batch of pending alerts.

        Args:
            limit: Maximum number of alerts to process

        Returns:
            Dict with processing statistics
        """
        # Get pending alerts
        pending_alerts = await AlertQueueRepository.get_pending_alerts(limit)

        if not pending_alerts:
            logger.debug("No pending alerts to process")
            return {"total": 0, "successful": 0, "failed": 0}

        logger.info("Processing pending alerts", count=len(pending_alerts))

        successful = 0
        failed = 0

        # Process alerts sequentially (can be parallelized if needed)
        for alert in pending_alerts:
            success = await self.process_alert(alert)
            if success:
                successful += 1
            else:
                failed += 1

        logger.info(
            "Finished processing alerts",
            total=len(pending_alerts),
            successful=successful,
            failed=failed
        )

        return {
            "total": len(pending_alerts),
            "successful": successful,
            "failed": failed
        }

    async def send_manual_notification(
        self,
        account_id: UUID,
        message: str,
        channels: List[str],
        phone: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send manual notification (bypass queue).

        Args:
            account_id: Account UUID
            message: Message content
            channels: List of channels to use
            phone: Optional phone override
            email: Optional email override

        Returns:
            Send result dict
        """
        # Get account details if phone/email not provided
        if not phone and not email:
            account = await AccountsRepository.get_by_id(account_id)
            if not account:
                raise ValueError("Account not found")

            phone = account.get("phone")
            email = account.get("email")

        results = {}

        for channel in channels:
            try:
                if channel == "whatsapp":
                    if not phone:
                        results[channel] = {"status": "failed", "error": "No phone number"}
                        continue

                    result = await self.comm_client.send_whatsapp(phone, message)
                    results[channel] = {
                        "status": "success",
                        "message_id": result.get("message_id")
                    }

                elif channel == "sms":
                    if not phone:
                        results[channel] = {"status": "failed", "error": "No phone number"}
                        continue

                    result = await self.comm_client.send_sms(phone, message)
                    results[channel] = {
                        "status": "success",
                        "message_id": result.get("message_id")
                    }

                elif channel == "email":
                    if not email:
                        results[channel] = {"status": "failed", "error": "No email address"}
                        continue

                    result = await self.comm_client.send_email(
                        email=email,
                        subject="Notificação Manual - Monitoring Options",
                        message=message
                    )
                    results[channel] = {
                        "status": "success",
                        "message_id": result.get("message_id")
                    }

            except Exception as e:
                logger.error(
                    "Failed to send manual notification",
                    channel=channel,
                    error=str(e)
                )
                results[channel] = {"status": "failed", "error": str(e)}

        return results


# Singleton instance
notification_service = NotificationService()
