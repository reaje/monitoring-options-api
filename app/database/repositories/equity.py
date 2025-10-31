"""Equity positions repository."""

from typing import List, Dict, Any, Optional
from uuid import UUID
import asyncpg
from app.config import settings
from app.database.repositories.base import BaseRepository
from app.database.repositories.accounts import AccountsRepository
from app.core.logger import logger


def _serialize_equity_row(row: asyncpg.Record) -> Optional[Dict[str, Any]]:
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
        "quantity": int(get_field("quantity")) if get_field("quantity") is not None else None,
        "avg_price": float(get_field("avg_price")) if get_field("avg_price") is not None else None,
        "created_at": (created.isoformat() + "Z") if created else None,
    }


class EquityRepository(BaseRepository):
    """Repository for equity_positions table."""

    table_name = "equity_positions"

    @staticmethod
    async def _get_conn(auth_user_id: Optional[str] = None):
        server_settings = {"search_path": settings.DB_SCHEMA}
        if auth_user_id:
            server_settings.update({
                "request.jwt.claim.sub": str(auth_user_id),
                "request.jwt.claim.role": "authenticated",
            })
        return await asyncpg.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            server_settings=server_settings,
        )

    @classmethod
    async def get_by_account_id(
        cls,
        account_id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            rows = await conn.fetch(
                f"""
                SELECT id, account_id, asset_id, quantity, avg_price, created_at
                FROM {settings.DB_SCHEMA}.equity_positions
                WHERE account_id = $1
                ORDER BY created_at DESC
                """,
                str(account_id),
            )
            return [_serialize_equity_row(r) for r in rows]
        finally:
            await conn.close()

    @classmethod
    async def get_by_asset_id(
        cls,
        asset_id: UUID,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            rows = await conn.fetch(
                f"""
                SELECT id, account_id, asset_id, quantity, avg_price, created_at
                FROM {settings.DB_SCHEMA}.equity_positions
                WHERE asset_id = $1
                ORDER BY created_at DESC
                """,
                str(asset_id),
            )
            return [_serialize_equity_row(r) for r in rows]
        finally:
            await conn.close()

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
                f"SELECT id, account_id, asset_id, quantity, avg_price, created_at FROM {settings.DB_SCHEMA}.equity_positions WHERE id = $1",
                str(id),
            )
            return _serialize_equity_row(row) if row else None
        finally:
            await conn.close()

    @classmethod
    async def get_user_equity(
        cls,
        equity_id: UUID,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        equity = await cls.get_by_id(equity_id, auth_user_id=user_id)
        if not equity:
            return None
        account_id = equity.get("account_id")
        if not await AccountsRepository.user_owns_account(UUID(account_id), user_id):
            logger.warning(
                "User attempted to access equity they don't own",
                user_id=str(user_id),
                equity_id=str(equity_id),
            )
            return None
        return equity

    @classmethod
    async def user_owns_equity(cls, equity_id: UUID, user_id: UUID) -> bool:
        equity = await cls.get_by_id(equity_id, auth_user_id=user_id)
        if not equity:
            return False
        account_id = UUID(equity.get("account_id"))
        return await AccountsRepository.user_owns_account(account_id, user_id)

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
                INSERT INTO {settings.DB_SCHEMA}.equity_positions (account_id, asset_id, quantity, avg_price)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (account_id, asset_id) DO UPDATE
                SET quantity = EXCLUDED.quantity, avg_price = EXCLUDED.avg_price
                RETURNING id, account_id, asset_id, quantity, avg_price, created_at
                """,
                str(data.get("account_id")),
                str(data.get("asset_id")),
                data.get("quantity"),
                data.get("avg_price"),
            )
            return _serialize_equity_row(row)
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
        for key in ["quantity", "avg_price"]:
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
                UPDATE {settings.DB_SCHEMA}.equity_positions
                SET {set_clause}
                WHERE id = $1
                RETURNING id, account_id, asset_id, quantity, avg_price, created_at
                """,
                str(id), *values,
            )
            if not row:
                from app.core.exceptions import NotFoundError
                raise NotFoundError(cls.table_name, id)
            return _serialize_equity_row(row)
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
                f"DELETE FROM {settings.DB_SCHEMA}.equity_positions WHERE id = $1",
                str(id),
            )
            return res.endswith(" 1")
        finally:
            await conn.close()

