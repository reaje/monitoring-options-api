"""Options positions repository."""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import date, datetime, timedelta
import asyncpg
from app.config import settings
from app.database.repositories.base import BaseRepository
from app.database.repositories.accounts import AccountsRepository
from app.core.logger import logger

JWT_GUC = "request.jwt.claim.sub"


def _serialize_position_row(row: asyncpg.Record) -> Dict[str, Any]:
    if row is None:
        return None
    is_dict = isinstance(row, dict)
    created = row.get("created_at") if is_dict else row["created_at"]
    def get_field(key):
        return row.get(key) if is_dict else row[key] if key in row.keys() else None
    return {
        "id": str(get_field("id")),
        "account_id": str(get_field("account_id")),
        "asset_id": str(get_field("asset_id")),
        "side": get_field("side"),
        "strategy": get_field("strategy"),
        "strike": float(get_field("strike")) if get_field("strike") is not None else None,
        "expiration": (get_field("expiration").isoformat() if isinstance(get_field("expiration"), (date, datetime)) else (str(get_field("expiration")) if get_field("expiration") is not None else None)),
        "quantity": int(get_field("quantity")) if get_field("quantity") is not None else None,
        "avg_premium": float(get_field("avg_premium")) if get_field("avg_premium") is not None else None,
        "status": get_field("status"),
        "notes": get_field("notes"),
        "created_at": (created.isoformat() + "Z") if created else None,
    }


class OptionsRepository(BaseRepository):
    """Repository for option_positions table."""

    table_name = "option_positions"
    @staticmethod
    async def _get_conn(auth_user_id: Optional[str] = None):
        server_settings = {"search_path": settings.DB_SCHEMA}
        if auth_user_id:
            server_settings.update({
                JWT_GUC: str(auth_user_id),
                "request.jwt.claim.role": "authenticated",
            })
        # Use full DATABASE_URL to avoid DNS issues seen with separate host/port on some environments
        return await asyncpg.connect(settings.DATABASE_URL, server_settings=server_settings)


    @classmethod
    async def get_by_account_id(
        cls,
        account_id: UUID,
        status: Optional[str] = None,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            sql = f"SELECT id, account_id, asset_id, side, strategy, strike, expiration, quantity, avg_premium, status, notes, created_at FROM {settings.DB_SCHEMA}.option_positions WHERE account_id = $1"
            params = [str(account_id)]
            if status:
                sql += " AND status = $2"
                params.append(status)
            sql += " ORDER BY expiration ASC"
            rows = await conn.fetch(sql, *params)
            return [_serialize_position_row(r) for r in rows]
        finally:
            await conn.close()

    @classmethod
    async def get_by_asset_id(
        cls,
        asset_id: UUID,
        status: Optional[str] = None,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            sql = f"SELECT id, account_id, asset_id, side, strategy, strike, expiration, quantity, avg_premium, status, notes, created_at FROM {settings.DB_SCHEMA}.option_positions WHERE asset_id = $1"
            params = [str(asset_id)]
            if status:
                sql += " AND status = $2"
                params.append(status)
            sql += " ORDER BY expiration ASC"
            rows = await conn.fetch(sql, *params)
            return [_serialize_position_row(r) for r in rows]
        finally:
            await conn.close()

    @classmethod
    async def get_open_positions(
        cls,
        account_id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        return await cls.get_by_account_id(account_id, status="OPEN", auth_user_id=auth_user_id)

    @classmethod
    async def get_expiring_soon(
        cls,
        account_id: UUID,
        days: int = 7,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        cutoff_date = (datetime.now() + timedelta(days=days)).date()
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            rows = await conn.fetch(
                f"""
                SELECT id, account_id, asset_id, side, strategy, strike, expiration, quantity, avg_premium, status, notes, created_at
                FROM {settings.DB_SCHEMA}.option_positions
                WHERE account_id = $1
                  AND status = 'OPEN'
                  AND expiration <= $2
                ORDER BY expiration ASC
                """,
                str(account_id), cutoff_date,
            )
            return [_serialize_position_row(r) for r in rows]
        finally:
            await conn.close()

    @classmethod
    async def get_user_position(
        cls,
        position_id: UUID,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        position = await cls.get_by_id(position_id, auth_user_id=user_id)
        if not position:
            return None
        account_id = position.get("account_id")
        if not await AccountsRepository.user_owns_account(UUID(account_id), user_id):
            logger.warning(
                "User attempted to access position they don't own",
                user_id=str(user_id),
                position_id=str(position_id),
            )
            return None
        return position

    @classmethod
    async def user_owns_position(cls, position_id: UUID, user_id: UUID) -> bool:
        position = await cls.get_by_id(position_id, auth_user_id=user_id)
        if not position:
            return False
    @classmethod
    async def get_by_id(
        cls,
        id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Optional[Dict[str, Any]]:
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            row = await conn.fetchrow(
                f"SELECT id, account_id, asset_id, side, strategy, strike, expiration, quantity, avg_premium, status, notes, created_at FROM {settings.DB_SCHEMA}.option_positions WHERE id = $1",
                str(id),
            )
            return _serialize_position_row(row) if row else None
        finally:
            await conn.close()

    @classmethod
    async def create(
        cls,
        data: Dict[str, Any],
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            row = await conn.fetchrow(
                f"""
                INSERT INTO {settings.DB_SCHEMA}.option_positions
                    (account_id, asset_id, side, strategy, strike, expiration, quantity, avg_premium, status, notes)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8, COALESCE($9, 'OPEN'), $10)
                RETURNING id, account_id, asset_id, side, strategy, strike, expiration, quantity, avg_premium, status, notes, created_at
                """,
                str(data.get("account_id")),
                str(data.get("asset_id")),
                data.get("side"),
                data.get("strategy"),
                data.get("strike"),
                data.get("expiration"),
                data.get("quantity"),
                data.get("avg_premium"),
                data.get("status"),
                data.get("notes"),
            )
            return _serialize_position_row(row)
        finally:
            await conn.close()

    @classmethod
    async def update(
        cls,
        id: UUID,
        data: Dict[str, Any],
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        if not data:
            existing = await cls.get_by_id(id, auth_user_id=auth_user_id)
            if not existing:
                from app.core.exceptions import NotFoundError
                raise NotFoundError(cls.table_name, id)
            return existing
        fields = []
        values = []
        for key in ["side", "strategy", "strike", "expiration", "quantity", "avg_premium", "status", "notes"]:
            if key in data:
                fields.append(key)
                values.append(data[key])
        if not fields:
            existing = await cls.get_by_id(id, auth_user_id=auth_user_id)
            if not existing:
                from app.core.exceptions import NotFoundError
                raise NotFoundError(cls.table_name, id)
            return existing
        set_clause = ", ".join([f"{f} = ${i+2}" for i, f in enumerate(fields)])
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            row = await conn.fetchrow(
                f"""
                UPDATE {settings.DB_SCHEMA}.option_positions
                SET {set_clause}
                WHERE id = $1
                RETURNING id, account_id, asset_id, side, strategy, strike, expiration, quantity, avg_premium, status, notes, created_at
                """,
                str(id), *values,
            )
            if not row:
                from app.core.exceptions import NotFoundError
                raise NotFoundError(cls.table_name, id)
            return _serialize_position_row(row)
        finally:
            await conn.close()

    @classmethod
    async def delete(
        cls,
        id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> bool:
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            res = await conn.execute(
                f"DELETE FROM {settings.DB_SCHEMA}.option_positions WHERE id = $1",
                str(id),
            )
            return res.endswith(" 1")
        finally:
            await conn.close()

    @classmethod
    async def close_position(
        cls,
        position_id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        return await cls.update(position_id, {"status": "CLOSED"}, auth_user_id=auth_user_id)

    @classmethod
    async def get_statistics(
        cls,
        account_id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics for account positions.
        """
        positions = await cls.get_by_account_id(account_id, auth_user_id=auth_user_id)

        total = len(positions)
        open_count = len([p for p in positions if p.get("status") == "OPEN"])
        closed_count = len([p for p in positions if p.get("status") == "CLOSED"])

        strategies: Dict[str, int] = {}
        for position in positions:
            strategy = position.get("strategy")
            if strategy is not None:
                strategies[strategy] = strategies.get(strategy, 0) + 1

        return {
            "total_positions": total,
            "open_positions": open_count,
            "closed_positions": closed_count,
            "strategies": strategies,
        }
