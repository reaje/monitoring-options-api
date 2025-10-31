"""Base repository class with common CRUD operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from app.database.supabase_client import supabase
from app.core.logger import logger
from app.core.exceptions import NotFoundError, DatabaseError


class BaseRepository:
    """Base repository with common CRUD operations."""

    table_name: str = None

    @classmethod
    def _ensure_table_name(cls):
        """Ensure table name is defined."""
        if not cls.table_name:
            raise ValueError(f"table_name must be defined in {cls.__name__}")

    @classmethod
    def _get_table(cls):
        """Get table with correct schema."""
        cls._ensure_table_name()
        # Get the table and manually set the schema
        table = supabase.table(cls.table_name)
        schema_name = getattr(supabase, 'schema_name', 'monitoring_options_operations')
        # Override the schema in the URL path
        table.session.headers['Accept-Profile'] = schema_name
        table.session.headers['Content-Profile'] = schema_name
        return table

    @classmethod
    async def get_all(
        cls,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get all records with optional filters.

        Args:
            filters: Dictionary of field: value filters
            limit: Maximum number of records to return
            offset: Number of records to skip
            order_by: Field to order by
            order_desc: Order descending if True

        Returns:
            List of records
        """
        try:
            query = cls._get_table().select("*")

            # Apply filters
            if filters:
                for field, value in filters.items():
                    query = query.eq(field, value)

            # Apply ordering
            if order_by:
                query = query.order(order_by, desc=order_desc)

            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)

            result = query.execute()

            logger.debug(
                f"Retrieved records from {cls.table_name}",
                count=len(result.data),
            )

            return result.data

        except Exception as e:
            logger.error(
                f"Failed to get records from {cls.table_name}",
                error=str(e),
            )
            raise DatabaseError(f"Failed to retrieve records: {str(e)}")

    @classmethod
    async def get_by_id(cls, id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get a record by ID.

        Args:
            id: Record UUID

        Returns:
            Record dict or None if not found
        """
        try:
            result = cls._get_table() \
                .select("*") \
                .eq("id", str(id)) \
                .single() \
                .execute()

            if not result.data:
                return None

            logger.debug(
                f"Retrieved record from {cls.table_name}",
                id=str(id),
            )

            return result.data

        except Exception as e:
            logger.error(
                f"Failed to get record from {cls.table_name}",
                id=str(id),
                error=str(e),
            )
            # If not found, return None instead of raising
            if "not found" in str(e).lower():
                return None
            raise DatabaseError(f"Failed to retrieve record: {str(e)}")

    @classmethod
    async def create(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new record.

        Args:
            data: Record data

        Returns:
            Created record
        """
        try:
            result = cls._get_table() \
                .insert(data) \
                .execute()

            if not result.data:
                raise DatabaseError("Failed to create record - no data returned")

            record = result.data[0]

            logger.info(
                f"Created record in {cls.table_name}",
                id=record.get("id"),
            )

            return record

        except Exception as e:
            logger.error(
                f"Failed to create record in {cls.table_name}",
                error=str(e),
            )
            raise DatabaseError(f"Failed to create record: {str(e)}")

    @classmethod
    async def update(cls, id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a record.

        Args:
            id: Record UUID
            data: Updated data

        Returns:
            Updated record

        Raises:
            NotFoundError: If record not found
        """
        try:
            # Check if record exists
            existing = await cls.get_by_id(id)
            if not existing:
                raise NotFoundError(cls.table_name, id)

            # Update record
            result = cls._get_table() \
                .update(data) \
                .eq("id", str(id)) \
                .execute()

            if not result.data:
                raise DatabaseError("Failed to update record - no data returned")

            record = result.data[0]

            logger.info(
                f"Updated record in {cls.table_name}",
                id=str(id),
            )

            return record

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to update record in {cls.table_name}",
                id=str(id),
                error=str(e),
            )
            raise DatabaseError(f"Failed to update record: {str(e)}")

    @classmethod
    async def delete(cls, id: UUID) -> bool:
        """
        Delete a record.

        Args:
            id: Record UUID

        Returns:
            True if deleted

        Raises:
            NotFoundError: If record not found
        """
        try:
            # Check if record exists
            existing = await cls.get_by_id(id)
            if not existing:
                raise NotFoundError(cls.table_name, id)

            # Delete record
            cls._get_table() \
                .delete() \
                .eq("id", str(id)) \
                .execute()

            logger.info(
                f"Deleted record from {cls.table_name}",
                id=str(id),
            )

            return True

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to delete record from {cls.table_name}",
                id=str(id),
                error=str(e),
            )
            raise DatabaseError(f"Failed to delete record: {str(e)}")

    @classmethod
    async def count(cls, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records with optional filters.

        Args:
            filters: Dictionary of field: value filters

        Returns:
            Number of records
        """
        try:
            query = cls._get_table().select("id", count="exact")

            # Apply filters
            if filters:
                for field, value in filters.items():
                    query = query.eq(field, value)

            result = query.execute()

            return result.count if hasattr(result, 'count') else len(result.data)

        except Exception as e:
            logger.error(
                f"Failed to count records in {cls.table_name}",
                error=str(e),
            )
            raise DatabaseError(f"Failed to count records: {str(e)}")

    @classmethod
    async def exists(cls, id: UUID) -> bool:
        """
        Check if a record exists.

        Args:
            id: Record UUID

        Returns:
            True if exists
        """
        record = await cls.get_by_id(id)
        return record is not None
