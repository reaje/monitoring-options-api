"""Notifier worker for processing alert queue and sending notifications."""

from typing import Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.notification_service import notification_service
from app.core.logger import logger
from app.config import settings


# Checagem de pregão da B3 via configuração (.env)
# Usa time zone e janela configuráveis em app.config.Settings
def _is_b3_market_open():
    tz = settings.MARKET_SESSION_TZ or "America/Sao_Paulo"
    sp_now = datetime.now(ZoneInfo(tz))
    if sp_now.weekday() >= 5:  # 0=Seg, 6=Dom
        return False, sp_now
    open_hhmm = (int(settings.MARKET_OPEN_HOUR), int(settings.MARKET_OPEN_MINUTE))
    close_hhmm = (int(settings.MARKET_CLOSE_HOUR), int(settings.MARKET_CLOSE_MINUTE))
    hhmm = (sp_now.hour, sp_now.minute)
    if hhmm < open_hhmm or hhmm >= close_hhmm:
        return False, sp_now
    return True, sp_now


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

        # Pular execucoes fora do horario de pregao da B3
        open_now, sp_now = _is_b3_market_open()
        if not open_now:
            logger.debug(
                "Notifier worker ignorado: mercado fechado (B3 10:00-18:00 America/Sao_Paulo)",
                sp_time=sp_now.isoformat(),
            )
            return {
                "run_number": self.run_count,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "skipped",
                "reason": "market_closed",
                "sp_time": sp_now.isoformat(),
            }


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
