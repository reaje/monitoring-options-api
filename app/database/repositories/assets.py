"""Assets repository."""

from typing import List, Dict, Any, Optional
from uuid import UUID
from app.database.repositories.base import BaseRepository
from app.database.repositories.accounts import AccountsRepository
from app.core.logger import logger


class AssetsRepository(BaseRepository):
    """Repository for assets table."""

    table_name = "assets"

    @classmethod
    async def get_by_account_id(cls, account_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all assets for an account.

        Args:
            account_id: Account UUID

        Returns:
            List of assets
        """
        return await cls.get_all(filters={"account_id": str(account_id)})

    @classmethod
    async def get_by_ticker(
        cls,
        account_id: UUID,
        ticker: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get an asset by ticker for a specific account.

        Args:
            account_id: Account UUID
            ticker: Asset ticker

        Returns:
            Asset dict or None if not found
        """
        assets = await cls.get_all(
            filters={
                "account_id": str(account_id),
                "ticker": ticker.upper()
            }
        )

        return assets[0] if assets else None

    @classmethod
    async def get_user_asset(
        cls,
        asset_id: UUID,
        user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get an asset if it belongs to a user's account.

        Args:
            asset_id: Asset UUID
            user_id: User UUID

        Returns:
            Asset dict or None if not found or doesn't belong to user
        """
        asset = await cls.get_by_id(asset_id)

        if not asset:
            return None

        # Check if user owns the account
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
        """
        Check if a user owns an asset (through account ownership).

        Args:
            asset_id: Asset UUID
            user_id: User UUID

        Returns:
            True if user owns asset
        """
        asset = await cls.get_by_id(asset_id)

        if not asset:
            return False

        account_id = UUID(asset.get("account_id"))
        return await AccountsRepository.user_owns_account(account_id, user_id)
