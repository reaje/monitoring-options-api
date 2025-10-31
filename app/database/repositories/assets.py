"""Assets repository."""

from typing import List, Dict, Any, Optional
from uuid import UUID
import asyncpg
from app.config import settings
from app.database.repositories.base import BaseRepository
from app.database.repositories.accounts import AccountsRepository
from app.core.logger import logger


class AssetsRepository(BaseRepository):
    """Repository for assets table."""

    table_name = "assets"

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
                SELECT id, account_id, ticker, created_at
                FROM {settings.DB_SCHEMA}.assets
                WHERE account_id = $1
                ORDER BY created_at DESC
                """,
                str(account_id),
            )
            return [
                {
                    "id": str(r["id"]),
                    "account_id": str(r["account_id"]),
                    "ticker": r["ticker"],
                    "created_at": (r["created_at"].isoformat() + "Z") if r["created_at"] else None,
                }
                for r in rows
            ]
        finally:
            await conn.close()

    @classmethod
    async def get_by_ticker(
        cls,
        account_id: UUID,
        ticker: str,
        *,
        auth_user_id: Optional[UUID] = None,
    ) -> Optional[Dict[str, Any]]:
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            row = await conn.fetchrow(
                f"""
                SELECT id, account_id, ticker, created_at
                FROM {settings.DB_SCHEMA}.assets
                WHERE account_id = $1 AND UPPER(ticker) = UPPER($2)
                LIMIT 1
                """,
                str(account_id), ticker,
            )
            return (
                {
                    "id": str(row["id"]),
                    "account_id": str(row["account_id"]),
                    "ticker": row["ticker"],
                    "created_at": (row["created_at"].isoformat() + "Z") if row["created_at"] else None,
                }
                if row
                else None
            )
        finally:
            await conn.close()

    @classmethod
    async def get_user_asset(
        cls,
        asset_id: UUID,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        asset = await cls.get_by_id(asset_id, auth_user_id=user_id)
        if not asset:
            return None
        account_id = asset.get("account_id")
        if not await AccountsRepository.user_owns_account(UUID(account_id), user_id):
            logger.warning(
                "User attempted to access asset they don't own",
                user_id=str(user_id),
                asset_id=str(asset_id),
            )
            return None
        return asset

    @classmethod
    async def user_owns_asset(cls, asset_id: UUID, user_id: UUID) -> bool:
        asset = await cls.get_by_id(asset_id, auth_user_id=user_id)
        if not asset:
            return False
        account_id = UUID(asset.get("account_id"))
        return await AccountsRepository.user_owns_account(account_id, user_id)

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
                f"SELECT id, account_id, ticker, created_at FROM {settings.DB_SCHEMA}.assets WHERE id = $1",
                str(id),
            )
            return (
                {
                    "id": str(row["id"]),
                    "account_id": str(row["account_id"]),
                    "ticker": row["ticker"],
                    "created_at": (row["created_at"].isoformat() + "Z") if row["created_at"] else None,
                }
                if row
                else None
            )
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
                INSERT INTO {settings.DB_SCHEMA}.assets (account_id, ticker)
                VALUES ($1, UPPER($2))
                RETURNING id, account_id, ticker, created_at
                """,
                str(data.get("account_id")), data.get("ticker"),
            )
            return {
                "id": str(row["id"]),
                "account_id": str(row["account_id"]),
                "ticker": row["ticker"],
                "created_at": (row["created_at"].isoformat() + "Z") if row["created_at"] else None,
            }
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
            # Nothing to update
            existing = await cls.get_by_id(id, auth_user_id=auth_user_id)
            if not existing:
                from app.core.exceptions import NotFoundError
                raise NotFoundError(cls.table_name, id)
            return existing
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            if "ticker" in data:
                row = await conn.fetchrow(
                    f"""
                    UPDATE {settings.DB_SCHEMA}.assets
                    SET ticker = UPPER($2)
                    WHERE id = $1
                    RETURNING id, account_id, ticker, created_at
                    """,
                    str(id), data["ticker"],
                )
            else:
                # No supported fields
                row = await conn.fetchrow(
                    f"SELECT id, account_id, ticker, created_at FROM {settings.DB_SCHEMA}.assets WHERE id = $1",
                    str(id),
                )
            if not row:
                from app.core.exceptions import NotFoundError
                raise NotFoundError(cls.table_name, id)
            return {
                "id": str(row["id"]),
                "account_id": str(row["account_id"]),
                "ticker": row["ticker"],
                "created_at": (row["created_at"].isoformat() + "Z") if row["created_at"] else None,
            }
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
                f"DELETE FROM {settings.DB_SCHEMA}.assets WHERE id = $1",
                str(id),
            )
            return res.endswith(" 1")
        finally:
            await conn.close()
