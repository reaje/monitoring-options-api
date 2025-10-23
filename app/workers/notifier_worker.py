"""Notifier worker for processing alert queue and sending notifications."""

from typing import Dict, Any
from datetime import datetime
from app.services.notification_service import notification_service
from app.core.logger import logger


class NotifierWorker:
    """Worker for processing pending alerts and sending notifications."""

    def __init__(self):
        """Initialize notifier worker."""
        self.run_count = 0
        self.batch_size = 100

    async def run(self) -> Dict[str, Any]:
        """
        Process pending alerts from queue.

        Returns:
            Statistics dict with processing results
        """
        self.run_count += 1

        logger.info(
            "Starting notifier worker run",
            run_number=self.run_count,
            timestamp=datetime.utcnow().isoformat()
        )

        try:
            # Process pending alerts using notification service
            results = await notification_service.process_pending_alerts(
                limit=self.batch_size
            )

            logger.info(
                "Notifier worker completed",
                run_number=self.run_count,
                total=results["total"],
                successful=results["successful"],
                failed=results["failed"]
            )

            return {
                "run_number": self.run_count,
                "timestamp": datetime.utcnow().isoformat(),
                "total_processed": results["total"],
                "successful": results["successful"],
                "failed": results["failed"],
                "status": "success"
            }

        except Exception as e:
            logger.error(
                "Notifier worker failed",
                run_number=self.run_count,
                error=str(e)
            )
            return {
                "run_number": self.run_count,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "status": "failed"
            }


# Singleton instance
notifier_worker = NotifierWorker()
