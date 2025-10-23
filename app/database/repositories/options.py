"""Options positions repository."""

from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import date
from app.database.repositories.base import BaseRepository
from app.database.repositories.accounts import AccountsRepository
from app.core.logger import logger


class OptionsRepository(BaseRepository):
    """Repository for option_positions table."""

    table_name = "option_positions"

    @classmethod
    async def get_by_account_id(
        cls,
        account_id: UUID,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all option positions for an account.

        Args:
            account_id: Account UUID
            status: Optional status filter (OPEN, CLOSED, EXPIRED)

        Returns:
            List of option positions
        """
        filters = {"account_id": str(account_id)}
        if status:
            filters["status"] = status

        return await cls.get_all(
            filters=filters,
            order_by="expiration",
            order_desc=False
        )

    @classmethod
    async def get_by_asset_id(
        cls,
        asset_id: UUID,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all option positions for an asset.

        Args:
            asset_id: Asset UUID
            status: Optional status filter

        Returns:
            List of option positions
        """
        filters = {"asset_id": str(asset_id)}
        if status:
            filters["status"] = status

        return await cls.get_all(
            filters=filters,
            order_by="expiration",
            order_desc=False
        )

    @classmethod
    async def get_open_positions(cls, account_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all open positions for an account.

        Args:
            account_id: Account UUID

        Returns:
            List of open positions
        """
        return await cls.get_by_account_id(account_id, status="OPEN")

    @classmethod
    async def get_expiring_soon(
        cls,
        account_id: UUID,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get positions expiring within specified days.

        Args:
            account_id: Account UUID
            days: Number of days (default 7)

        Returns:
            List of positions expiring soon
        """
        from datetime import datetime, timedelta
        from app.database.supabase_client import supabase

        cutoff_date = (datetime.now() + timedelta(days=days)).date()

        result = supabase.table(cls.table_name) \
            .select("*") \
            .eq("account_id", str(account_id)) \
            .eq("status", "OPEN") \
            .lte("expiration", cutoff_date.isoformat()) \
            .order("expiration") \
            .execute()

        return result.data

    @classmethod
    async def get_user_position(
        cls,
        position_id: UUID,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get a position if it belongs to a user's account.

        Args:
            position_id: Position UUID
            user_id: User UUID

        Returns:
            Position dict or None if not found or doesn't belong to user
        """
        position = await cls.get_by_id(position_id)

        if not position:
            return None

        # Check if user owns the account
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
        """
        Check if a user owns a position (through account ownership).

        Args:
            position_id: Position UUID
            user_id: User UUID

        Returns:
            True if user owns position
        """
        position = await cls.get_by_id(position_id)

        if not position:
            return False

        account_id = UUID(position.get("account_id"))
        return await AccountsRepository.user_owns_account(account_id, user_id)

    @classmethod
    async def close_position(cls, position_id: UUID) -> Dict[str, Any]:
        """
        Close a position (set status to CLOSED).

        Args:
            position_id: Position UUID

        Returns:
            Updated position
        """
        return await cls.update(position_id, {"status": "CLOSED"})

    @classmethod
    async def get_statistics(cls, account_id: UUID) -> Dict[str, Any]:
        """
        Get statistics for account positions.

        Args:
            account_id: Account UUID

        Returns:
            Statistics dict
        """
        positions = await cls.get_by_account_id(account_id)

        total = len(positions)
        open_count = len([p for p in positions if p["status"] == "OPEN"])
        closed_count = len([p for p in positions if p["status"] == "CLOSED"])

        # Group by strategy
        strategies = {}
        for position in positions:
            strategy = position["strategy"]
            strategies[strategy] = strategies.get(strategy, 0) + 1

        return {
            "total_positions": total,
            "open_positions": open_count,
            "closed_positions": closed_count,
            "strategies": strategies,
        }
