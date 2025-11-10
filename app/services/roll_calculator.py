"""Roll calculator service for generating roll suggestions."""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, date, timedelta
from calendar import monthrange
from app.database.repositories.options import OptionsRepository
from app.database.repositories.rules import RulesRepository
from app.core.logger import logger
from app.services.market_data import market_data_provider


class RollCalculator:
    """Service for calculating roll suggestions."""

    def __init__(self):
        """Initialize roll calculator."""
        pass

    async def get_roll_preview(
        self,
        position_id: UUID,
        market_data: Optional[Dict[str, Any]] = None,
        *,
        auth_user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Generate roll preview with suggestions for a position.

        Args:
            position_id: Position UUID
            market_data: Optional market data (if None, uses mock data)

        Returns:
            Preview dict with current position and suggestions
        """
        # Get current position
        position = await OptionsRepository.get_by_id(position_id, auth_user_id=auth_user_id)

        if not position:
            raise ValueError("Position not found")

        # Get account rules
        account_id = UUID(position["account_id"])
        rules = await RulesRepository.get_active_rules(account_id, auth_user_id=auth_user_id)

        # Use first rule or defaults
        rule = rules[0] if rules else self._get_default_rule()

        # Get current market data (preferir dados ao vivo via MT5; sem mocks)
        if market_data is None:
            market_data = await self._get_live_market_data(position, auth_user_id)

        # Normalize market data and handle absence gracefully
        safe_md = market_data or {}
        try:
            cur_px = float(safe_md.get("current_price") or 0)
        except Exception:
            cur_px = 0.0

        if cur_px <= 0:
            # Sem dado de preço atual: não geramos sugestões, mas retornamos métricas básicas
            current_metrics = self._calculate_position_metrics(position, safe_md)
            logger.info(
                "Roll preview generated (no market data)",
                position_id=str(position_id),
                suggestions_count=0,
            )
            return {
                "current_position": {
                    **position,
                    **current_metrics,
                },
                "suggestions": [],
                "market_data": safe_md,
                "rule_used": rule,
            }

        # Generate suggestions
        suggestions = await self._generate_suggestions(
            position,
            rule,
            safe_md,
        )

        # Calculate current position metrics
        current_metrics = self._calculate_position_metrics(
            position,
            safe_md,
        )

        logger.info(
            "Roll preview generated",
            position_id=str(position_id),
            suggestions_count=len(suggestions)
        )

        return {
            "current_position": {
                **position,
                **current_metrics
            },
            "suggestions": suggestions,
            "market_data": safe_md,
            "rule_used": rule
        }

    async def _generate_suggestions(
        self,
        position: Dict[str, Any],
        rule: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Gerar sugestões de rolagem com dados reais do MT5 (sem mocks).
        """
        suggestions: List[Dict[str, Any]] = []

        current_price = float(market_data.get("current_price") or 0)
        if current_price <= 0:
            return suggestions

        current_strike = float(position.get("strike", 0) or 0)
        side = str(position.get("side") or "CALL").upper()
        option_type = "call" if side == "CALL" else "put"

        # Ticker do ativo
        ticker = market_data.get("ticker") or position.get("ticker")
        if not ticker:
            # Sem ticker não há como buscar cadeia
            return suggestions

        # Alvos de OTM (%)
        otm_low = float(rule.get("target_otm_pct_low", 0.03))
        otm_high = float(rule.get("target_otm_pct_high", 0.08))

        # Faixa de DTE
        dte_min = int(rule.get("dte_min", 21))
        dte_max = int(rule.get("dte_max", 45))

        # Faixa de strikes alvo (em preço absoluto)
        if side == "CALL":
            strike_low = current_price * (1 + otm_low)
            strike_high = current_price * (1 + otm_high)
        else:
            strike_low = current_price * (1 - otm_high)
            strike_high = current_price * (1 - otm_low)

        # Custo de recompra da perna atual (mid do book)
        try:
            from MT5.storage import get_latest_option_quote
            buyback_q = get_latest_option_quote(
                ticker=ticker,
                strike=current_strike,
                expiration=str(position.get("expiration")),
                option_type=option_type,
            )
            buyback_mid = None
            if buyback_q:
                b_bid = float(buyback_q.get("bid") or 0)
                b_ask = float(buyback_q.get("ask") or 0)
                b_last = float(buyback_q.get("last") or 0)
                buyback_mid = (b_bid + b_ask) / 2 if (b_bid and b_ask) else (b_last or b_bid or b_ask)
        except Exception:
            buyback_mid = None

        # Fallback: se não houver preço MT5 da perna atual, tenta provider híbrido (brapi/BS)
        if buyback_mid is None:
            try:
                oq = await market_data_provider.get_option_quote(
                    ticker=ticker,
                    strike=current_strike,
                    expiration=str(position.get("expiration")),
                    option_type=option_type,
                )
                p_bid = float(oq.get("bid") or 0)
                p_ask = float(oq.get("ask") or 0)
                p_prem = float(oq.get("premium") or 0)
                buyback_mid = (p_bid + p_ask) / 2 if (p_bid and p_ask) else (p_prem or p_bid or p_ask)
            except Exception:
                buyback_mid = None

        if buyback_mid is None:
            # Sem preço de recompra confiável não geramos sugestões
            return suggestions

        # Candidatos de vencimento (3ª sexta) dentro da janela de DTE
        candidate_exps = self._candidate_expirations_in_range(dte_min, dte_max)
        if not candidate_exps:
            return suggestions

        # Buscar cadeia de opções recente do cache do MT5
        try:
            from MT5.storage import get_all_option_quotes
            all_opts = get_all_option_quotes(max_age_seconds=180)
        except Exception:
            all_opts = {}

        # Filtrar por ticker, tipo, vencimento e strike dentro da faixa alvo
        from datetime import date as _date
        today = _date.today()
        for entry in all_opts.values():
            if (entry.get("ticker") or "").upper() != ticker.upper():
                continue
            if (entry.get("option_type") or "").lower() != option_type:
                continue
            exp = str(entry.get("expiration") or "")
            if exp not in candidate_exps:
                continue
            strike = float(entry.get("strike") or 0)
            if strike <= 0:
                continue
            if not (min(strike_low, strike_high) <= strike <= max(strike_low, strike_high)):
                continue

            bid = float(entry.get("bid") or 0)
            ask = float(entry.get("ask") or 0)
            last = float(entry.get("last") or 0)
            mid = (bid + ask) / 2 if (bid and ask) else (last or bid or ask)
            if not mid or mid <= 0:
                continue

            # DTE real do vencimento
            try:
                dte = (datetime.fromisoformat(exp).date() - today).days
            except Exception:
                dte = 0
            if dte < dte_min or dte > dte_max:
                continue

            # OTM % relativo ao subjacente
            otm_pct = abs(strike - current_price) / current_price

            net_credit = mid - buyback_mid

            # Spread % quando disponível
            spread = None
            if bid and ask and mid:
                try:
                    spread = (ask - bid) / mid
                except Exception:
                    spread = None

            score = self._calculate_suggestion_score(
                otm_pct,
                net_credit,
                dte,
                rule,
            )

            suggestions.append({
                "strike": round(strike, 2),
                "expiration": exp,
                "dte": int(dte),
                "otm_pct": round(otm_pct * 100, 2),
                "premium": round(mid, 2),
                "net_credit": round(net_credit, 2),
                "spread": round(spread, 4) if spread is not None else None,
                "volume": entry.get("volume"),
                "oi": None,
                "score": round(score, 2),
            })

        # Fallback: se nada do MT5 gerou sugestão, estima prêmios via provider (BS/brapi)
        if not suggestions:
            def _round_to_05(x: float) -> float:
                try:
                    return round(x * 2) / 2.0
                except Exception:
                    return x

            target_otm = (otm_low + otm_high) / 2.0
            # Strike alvo (meio da faixa OTM)
            if side == "CALL":
                target_strike = _round_to_05(current_price * (1 + target_otm))
            else:
                target_strike = _round_to_05(current_price * (1 - target_otm))

            for exp in candidate_exps[:3]:  # limitar para reduzir latência
                try:
                    oq = await market_data_provider.get_option_quote(
                        ticker=ticker,
                        strike=target_strike,
                        expiration=exp,
                        option_type=option_type,
                    )
                    b = float(oq.get("bid") or 0)
                    a = float(oq.get("ask") or 0)
                    prem = float(oq.get("premium") or 0)
                    mid = (b + a) / 2 if (b and a) else (prem or b or a)
                    if not mid or mid <= 0:
                        continue

                    # DTE
                    try:
                        dte = (datetime.fromisoformat(exp).date() - today).days
                    except Exception:
                        dte = 0
                    if dte < dte_min or dte > dte_max:
                        continue

                    otm_pct = abs(target_strike - current_price) / current_price
                    net_credit = mid - buyback_mid
                    spread = None
                    if b and a and mid:
                        try:
                            spread = (a - b) / mid
                        except Exception:
                            spread = None

                    score = self._calculate_suggestion_score(otm_pct, net_credit, dte, rule)

                    suggestions.append({
                        "strike": round(target_strike, 2),
                        "expiration": exp,
                        "dte": int(dte),
                        "otm_pct": round(otm_pct * 100, 2),
                        "premium": round(mid, 2),
                        "net_credit": round(net_credit, 2),
                        "spread": round(spread, 4) if spread is not None else None,
                        "volume": oq.get("volume"),
                        "oi": None,
                        "source": oq.get("source") or "fallback",
                        "score": round(score, 2),
                    })
                except Exception:
                    continue

        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions[:5]




    def _calculate_suggestion_score(
        self,
        otm_pct: float,
        net_credit: float,
        dte: int,
        rule: Dict[str, Any]
    ) -> float:
        """
        Calculate score for a roll suggestion.

        Higher score = better suggestion

        Args:
            otm_pct: Out-of-money percentage
            net_credit: Net credit of the roll
            dte: Days to expiration
            rule: Roll rule

        Returns:
            Score (0-100)
        """
        score = 0.0

        # Reward net credit (40 points max)
        if net_credit > 0:
            # More credit = higher score
            score += min(net_credit * 10, 40)

        # Reward OTM in target range (30 points max)
        target_otm_low = rule.get("target_otm_pct_low", 0.03)

        target_otm_high = rule.get("target_otm_pct_high", 0.08)
        target_otm = (target_otm_low + target_otm_high) / 2

        otm_distance = abs(otm_pct - target_otm)
        otm_score = max(0, 30 - (otm_distance * 300))
        score += otm_score

        # Reward DTE in target range (20 points max)
        dte_min = rule.get("dte_min", 21)
        dte_max = rule.get("dte_max", 45)
        target_dte = (dte_min + dte_max) / 2

        dte_distance = abs(dte - target_dte)


        dte_score = max(0, 20 - (dte_distance / 2))
        score += dte_score

        # Bonus for liquidity (10 points max) - currently mock
        score += 10

        return score






    def _calculate_position_metrics(
        self,
        position: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate metrics for current position.

        Args:
            position: Position dict
            market_data: Market data

        Returns:
            Metrics dict
        """
        current_price = float((market_data or {}).get("current_price") or 0)
        strike = float(position.get("strike", 0))
        side = position.get("side", "CALL")

        # Calculate DTE
        dte = self._calculate_dte(position.get("expiration"))

        # Calculate OTM percentage (evitar divisão por zero)
        if current_price > 0:
            otm_pct = abs(strike - current_price) / current_price * 100
        else:
            otm_pct = None

        # Determine if ITM or OTM (somente se houver preço)
        if current_price > 0:
            if side == "CALL":
                is_itm = current_price > strike
            else:
                is_itm = current_price < strike
        else:
            is_itm = None

        # Calculate P&L
        avg_premium = float(position.get("avg_premium", 0))
        quantity = int(position.get("quantity", 0))

        # Current value (market mid when available)
        current_premium = None
        try:
            ticker = (market_data or {}).get("ticker") or position.get("ticker")
            if ticker:
                from MT5.storage import get_latest_option_quote
                q = get_latest_option_quote(
                    ticker=ticker,
                    strike=strike,
                    expiration=str(position.get("expiration")),
                    option_type=("call" if side == "CALL" else "put"),
                )
                if q:
                    b = float(q.get("bid") or 0)
                    a = float(q.get("ask") or 0)
                    l = float(q.get("last") or 0)
                    m = (b + a) / 2 if (b and a) else (l or b or a)
                    if m and m > 0:
                        current_premium = m
        except Exception:
            pass
        if current_premium is None:
            current_premium = 0.0

        # P&L = (premium received - current value) * quantity * 100
        pnl = (avg_premium - current_premium) * quantity * 100

        return {
            "dte": dte,
            "otm_pct": (round(otm_pct, 2) if otm_pct is not None else None),
            "is_itm": is_itm,
            "current_premium": round(current_premium, 2),
            "pnl": round(pnl, 2),
            "current_price": round(current_price, 2),
        }

    def _calculate_dte(self, expiration) -> int:
        """Calculate days to expiration."""
        if isinstance(expiration, str):
            expiration = datetime.fromisoformat(expiration).date()
        elif isinstance(expiration, datetime):
            expiration = expiration.date()

        today = date.today()
        return (expiration - today).days


    async def _get_live_market_data(self, position: Dict[str, Any], auth_user_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
        """
        Busca dado de mercado ao vivo do subjacente via MT5.storage.
        Retorna None se indisponível.
        """
        try:
            from MT5.storage import get_latest_quote
            from app.database.repositories.assets import AssetsRepository
        except Exception:
            return None
        try:
            ticker = position.get("ticker")
            if not ticker:
                asset_id = position.get("asset_id")
                if asset_id:
                    asset = await AssetsRepository.get_by_id(UUID(str(asset_id)), auth_user_id=auth_user_id)
                    if asset:
                        ticker = asset.get("ticker")
            if not ticker:
                return None
            q = get_latest_quote(ticker)
            if not q:
                return None
            bid = float(q.get("bid") or 0)
            ask = float(q.get("ask") or 0)
            last = float(q.get("last") or 0)
            mid = (bid + ask) / 2 if (bid and ask) else (last or bid or ask)
            if not mid or mid <= 0:
                return None
            return {
                "ticker": ticker,
                "current_price": round(mid, 2),
                "bid": bid or None,
                "ask": ask or None,
                "volume": q.get("volume"),
                "timestamp": q.get("ts") or q.get("timestamp"),
            }
        except Exception:
            return None


    def _get_default_rule(self) -> Dict[str, Any]:
        """Get default rule configuration."""
        return {
            "delta_threshold": 0.60,
            "dte_min": 21,
            "dte_max": 45,
            "target_otm_pct_low": 0.03,
            "target_otm_pct_high": 0.08,
            "min_volume": 1000,
            "max_spread": 0.05,
            "min_oi": 5000
        }


    def _candidate_expirations_in_range(self, dte_min: int, dte_max: int) -> List[str]:
        """
        Datas das terceiras sextas-feiras com DTE dentro do intervalo.
        """
        today = date.today()
        candidates: List[str] = []
        for moff in range(0, 12):
            year = today.year + ((today.month - 1 + moff) // 12)
            month = ((today.month - 1 + moff) % 12) + 1
            first = date(year, month, 1)
            first_wd = first.weekday()  # Monday=0 ... Sunday=6
            offset_to_first_friday = (4 - first_wd + 7) % 7  # Friday=4
            third_friday = first + timedelta(days=offset_to_first_friday + 14)
            dte = (third_friday - today).days
            if dte_min <= dte <= dte_max:
                candidates.append(third_friday.isoformat())
        return candidates


# Singleton instance
roll_calculator = RollCalculator()
