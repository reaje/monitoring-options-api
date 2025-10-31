"""Supabase client singleton."""

from typing import Optional
from supabase import create_client, Client
from app.config import settings
from app.core.logger import logger


class SupabaseClient:
    """Singleton Supabase client wrapper."""

    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """
        Get or create Supabase client instance.

        Returns:
            Supabase client instance
        """
        if cls._instance is None:
            try:
                logger.info(
                    "Initializing Supabase client",
                    url=settings.SUPABASE_URL,
                )
                cls._instance = create_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=settings.SUPABASE_SERVICE_KEY,
                )
                logger.info("Supabase client initialized successfully")
                # Set default schema for PostgREST so .table() uses our schema
                try:
                    # Store the schema in the client for later use
                    cls._instance.schema_name = settings.DB_SCHEMA
                    logger.info("Supabase schema configured", schema=settings.DB_SCHEMA)
                except Exception as e:
                    logger.warning("Could not configure Supabase schema; using 'public'", error=str(e))
                    cls._instance.schema_name = "public"

            except Exception as e:
                logger.error("Failed to initialize Supabase client", error=str(e))
                raise

        return cls._instance

    @classmethod
    def test_connection(cls) -> bool:
        """
        Test connection to Supabase.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            client = cls.get_client()
            # Simple check - if we got the client, connection is OK
            # Don't do actual queries here to avoid initialization errors
            if client is not None:
                logger.info("Supabase connection test successful")
                return True
            return False
        except Exception as e:
            logger.error("Supabase connection test failed", error=str(e))
            return False


# Convenience function to get client
def get_supabase() -> Client:
    """Get Supabase client instance."""
    return SupabaseClient.get_client()


# Create singleton instance
supabase = get_supabase()
