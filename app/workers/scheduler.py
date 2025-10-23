"""APScheduler configuration and job management."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from app.config import settings
from app.core.logger import logger
from app.workers.monitor_worker import monitor_worker
from app.workers.notifier_worker import notifier_worker


class WorkerScheduler:
    """Scheduler for background workers."""

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    def setup_jobs(self):
        """Setup all scheduled jobs."""
        logger.info("Setting up scheduler jobs...")

        # Monitor Worker - Every 5 minutes (configurable)
        self.scheduler.add_job(
            func=monitor_worker.run,
            trigger=IntervalTrigger(
                minutes=settings.MONITOR_INTERVAL_MINUTES
            ),
            id="monitor_positions",
            name="Monitor Option Positions",
            replace_existing=True,
            max_instances=1,  # Prevent concurrent runs
            coalesce=True,  # If missed, run once instead of multiple times
        )

        # Notifier Worker - Every 30 seconds (configurable)
        self.scheduler.add_job(
            func=notifier_worker.run,
            trigger=IntervalTrigger(
                seconds=settings.NOTIFIER_INTERVAL_SECONDS
            ),
            id="process_alerts",
            name="Process Alert Queue",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

        # Cleanup Worker - Daily at 3 AM
        self.scheduler.add_job(
            func=self._cleanup_old_data,
            trigger=CronTrigger(hour=3, minute=0),
            id="cleanup_data",
            name="Cleanup Old Data",
            replace_existing=True,
        )

        # Expire Positions Worker - Daily at 1 AM
        self.scheduler.add_job(
            func=self._expire_positions,
            trigger=CronTrigger(hour=1, minute=0),
            id="expire_positions",
            name="Expire Old Positions",
            replace_existing=True,
        )

        logger.info(
            "Scheduler jobs configured",
            jobs=len(self.scheduler.get_jobs()),
            monitor_interval_min=settings.MONITOR_INTERVAL_MINUTES,
            notifier_interval_sec=settings.NOTIFIER_INTERVAL_SECONDS
        )

    def start(self):
        """Start the scheduler."""
        if not self.is_running:
            self.setup_jobs()
            self.scheduler.start()
            self.is_running = True

            logger.info(
                "Scheduler started",
                next_run=datetime.now().isoformat()
            )

            # Log next run times for all jobs
            for job in self.scheduler.get_jobs():
                logger.info(
                    "Scheduled job",
                    job_id=job.id,
                    job_name=job.name,
                    next_run=job.next_run_time.isoformat() if job.next_run_time else None
                )

    def stop(self):
        """Stop the scheduler."""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Scheduler stopped")

    def pause_job(self, job_id: str):
        """Pause a specific job."""
        try:
            self.scheduler.pause_job(job_id)
            logger.info("Job paused", job_id=job_id)
        except Exception as e:
            logger.error("Failed to pause job", job_id=job_id, error=str(e))

    def resume_job(self, job_id: str):
        """Resume a paused job."""
        try:
            self.scheduler.resume_job(job_id)
            logger.info("Job resumed", job_id=job_id)
        except Exception as e:
            logger.error("Failed to resume job", job_id=job_id, error=str(e))

    def get_job_status(self, job_id: str) -> dict:
        """Get status of a specific job."""
        job = self.scheduler.get_job(job_id)
        if job:
            return {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
        return None

    def get_all_jobs_status(self) -> list:
        """Get status of all jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs

    async def _cleanup_old_data(self):
        """Clean up old alerts and logs (runs daily at 3 AM)."""
        logger.info("Starting cleanup worker")

        try:
            from app.database.repositories.alerts import AlertQueueRepository
            from app.database.repositories.alert_logs import AlertLogsRepository

            # Cleanup old sent alerts (30 days)
            alerts_deleted = await AlertQueueRepository.cleanup_old_alerts(days=30)

            # Cleanup old successful logs (90 days)
            logs_deleted = await AlertLogsRepository.cleanup_old_logs(days=90)

            logger.info(
                "Cleanup completed",
                alerts_deleted=alerts_deleted,
                logs_deleted=logs_deleted
            )

        except Exception as e:
            logger.error("Cleanup worker failed", error=str(e))

    async def _expire_positions(self):
        """Expire old positions (runs daily at 1 AM)."""
        logger.info("Starting expire positions worker")

        try:
            from app.database.supabase_client import supabase

            # Call the database function to expire positions
            result = supabase.rpc(
                "expire_old_positions",
                {}
            ).execute()

            expired_count = result.data if result.data else 0

            logger.info(
                "Positions expired",
                count=expired_count
            )

        except Exception as e:
            logger.error("Expire positions worker failed", error=str(e))


# Singleton instance
worker_scheduler = WorkerScheduler()
