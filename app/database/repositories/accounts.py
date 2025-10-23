"""Accounts repository."""

from typing import List, Dict, Any, Optional
from uuid import UUID
import asyncpg
from app.config import settings
from app.database.repositories.base import BaseRepository
from app.core.logger import logger

JWT_GUC = "request.jwt.claim.sub"


def _serialize_account_row(row: asyncpg.Record) -> Dict[str, Any]:
    """Convert asyncpg row to JSON-serializable dict for Account."""
    if row is None:
        return None
    is_dict = isinstance(row, dict)
    created = row.get("created_at") if is_dict else row["created_at"]
    def get_field(key):
        return row.get(key) if is_dict else row[key] if key in row.keys() else None
    return {
        "id": str(get_field("id")),
        "user_id": str(get_field("user_id")),
        "name": get_field("name"),
        "broker": get_field("broker"),
        "account_number": get_field("account_number"),
        "created_at": (created.isoformat() + "Z") if created else None,
    }


class AccountsRepository(BaseRepository):
    """Repository for accounts table."""

    table_name = "accounts"

    @staticmethod
    async def _get_conn(auth_user_id: Optional[str] = None):
        server_settings = {"search_path": settings.DB_SCHEMA}
        if auth_user_id:
            server_settings.update({
                JWT_GUC: str(auth_user_id),
                "request.jwt.claim.role": "authenticated",
            })
        conn = await asyncpg.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            server_settings=server_settings,
        )
        return conn

    @classmethod
    async def get_by_user_id(cls, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all accounts for a user.

        Args:
            user_id: User UUID

        Returns:
            List of accounts
        """
        conn = await cls._get_conn(auth_user_id=str(user_id))
        try:
            rows = await conn.fetch(
                f"""
                SELECT id, user_id, name, broker, account_number, created_at
                FROM {settings.DB_SCHEMA}.accounts
                WHERE user_id = $1
                ORDER BY created_at DESC
                """,
                str(user_id),
            )
            return [_serialize_account_row(r) for r in rows]
        finally:
            await conn.close()

    @classmethod
    async def create(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new account (direct PG)."""
        uid = str(data.get("user_id")) if data.get("user_id") else None
        conn = await cls._get_conn(auth_user_id=uid)
        try:
            row = await conn.fetchrow(
                f"""
                INSERT INTO {settings.DB_SCHEMA}.accounts (user_id, name, broker, account_number)
                VALUES ($1, $2, $3, $4)
                RETURNING id, user_id, name, broker, account_number, created_at
                """,
                str(data.get("user_id")),
                data.get("name"),
                data.get("broker"),
                data.get("account_number"),
            )
            return _serialize_account_row(row)
        finally:
            await conn.close()

    @classmethod
    async def get_by_id(cls, id: UUID, *, auth_user_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
        """Get an account by ID (direct PG)."""
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            row = await conn.fetchrow(
                f"""
                SELECT id, user_id, name, broker, account_number, created_at
                FROM {settings.DB_SCHEMA}.accounts
                WHERE id = $1
                """,
                str(id),
            )
            return _serialize_account_row(row) if row else None
        finally:
            await conn.close()

    @classmethod
    async def update(cls, id: UUID, data: Dict[str, Any], *, auth_user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Update an account (supports updating name)."""
        fields: List[str] = []
        values: List[Any] = []
        if "name" in data and data["name"] is not None:
            fields.append("name")
            values.append(data["name"])
        if "broker" in data:
            fields.append("broker")
            values.append(data.get("broker"))
        if "account_number" in data:
            fields.append("account_number")
            values.append(data.get("account_number"))
        if not fields:
            # Nothing to update; return current record
            existing = await cls.get_by_id(id, auth_user_id=auth_user_id)
            if existing is None:
                from app.core.exceptions import NotFoundError
                raise NotFoundError(cls.table_name, id)
            return existing
        # Build dynamic SET clause
        set_clause = ", ".join([f"{f} = ${i+2}" for i, f in enumerate(fields)])
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            row = await conn.fetchrow(
                f"""
                UPDATE {settings.DB_SCHEMA}.accounts
                SET {set_clause}
                WHERE id = $1
                RETURNING id, user_id, name, broker, account_number, created_at
                """,
                str(id),
                *values,
            )
            if not row:
                from app.core.exceptions import NotFoundError
                raise NotFoundError(cls.table_name, id)
            return _serialize_account_row(row)
        finally:
            await conn.close()

    @classmethod
    async def delete(cls, id: UUID, *, auth_user_id: Optional[UUID] = None) -> bool:
        """Delete an account by ID (direct PG)."""
        conn = await cls._get_conn(auth_user_id=str(auth_user_id) if auth_user_id else None)
        try:
            result = await conn.execute(
                f"DELETE FROM {settings.DB_SCHEMA}.accounts WHERE id = $1",
                str(id),
            )
            # asyncpg returns a status string like 'DELETE 1'
            return result.endswith(" 1")
        finally:
            await conn.close()

    @classmethod
    async def get_user_account(
        cls,
        account_id: UUID,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get an account if it belongs to the user.

        Args:
            account_id: Account UUID
            user_id: User UUID

        Returns:
            Account dict or None if not found or doesn't belong to user
        """
        account = await cls.get_by_id(account_id, auth_user_id=user_id)

        if not account:
            return None

        # Check ownership
        if account.get("user_id") != str(user_id):
            logger.warning(
                "User attempted to access account they don't own",
                user_id=str(user_id),
                account_id=str(account_id),
            )
            return None

        return account

    @classmethod
    async def user_owns_account(cls, account_id: UUID, user_id: UUID) -> bool:
        """
        Check if a user owns an account.

        Args:
            account_id: Account UUID
            user_id: User UUID

        Returns:
            True if user owns account
        """
        account = await cls.get_by_id(account_id)

        if not account:
            return False

        return account.get("user_id") == str(user_id)
