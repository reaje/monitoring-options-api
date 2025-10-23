"""Worker management routes."""

from sanic import Blueprint, response
from sanic.request import Request
from sanic_ext import openapi
from app.workers.scheduler import worker_scheduler
from app.core.logger import logger
from app.core.exceptions import ValidationError
from app.middleware.auth_middleware import require_auth


workers_bp = Blueprint("workers", url_prefix="/api/workers")


@workers_bp.get("/status")
@openapi.tag("Workers")
@openapi.summary("Get workers status")
@openapi.description("Get status of all background workers and scheduled jobs")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Workers status information")
@openapi.response(401, description="Not authenticated")
@require_auth
async def get_workers_status(request: Request):
    """
    Get status of all background workers.

    Returns:
        200: Workers status
        401: Not authenticated
    """
    jobs = worker_scheduler.get_all_jobs_status()

    return response.json(
        {
            "scheduler_running": worker_scheduler.is_running,
            "jobs": jobs,
            "total_jobs": len(jobs)
        },
        status=200,
    )


@workers_bp.get("/status/<job_id>")
@openapi.tag("Workers")
@openapi.summary("Get job status by ID")
@openapi.description("Get status of a specific background job")
@openapi.parameter("job_id", str, "path", description="Job ID (e.g., monitor_positions, process_alerts)")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Job status information")
@openapi.response(401, description="Not authenticated")
@openapi.response(404, description="Job not found")
@require_auth
async def get_job_status(request: Request, job_id: str):
    """
    Get status of a specific job.

    Returns:
        200: Job status
        401: Not authenticated
        404: Job not found
    """
    job_status = worker_scheduler.get_job_status(job_id)

    if not job_status:
        return response.json(
            {"error": "Job not found"},
            status=404
        )

    return response.json(
        {"job": job_status},
        status=200,
    )


@workers_bp.post("/jobs/<job_id>/pause")
@openapi.tag("Workers")
@openapi.summary("Pause background job")
@openapi.description("Pause a background job")
@openapi.parameter("job_id", str, "path", description="Job ID to pause")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Job paused successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(422, description="Failed to pause job")
@require_auth
async def pause_job(request: Request, job_id: str):
    """
    Pause a background job.

    Returns:
        200: Job paused
        401: Not authenticated
    """
    try:
        worker_scheduler.pause_job(job_id)

        logger.info(
            "Job paused via API",
            job_id=job_id,
            user_id=request.ctx.user["id"]
        )

        return response.json(
            {"message": f"Job {job_id} paused successfully"},
            status=200,
        )

    except Exception as e:
        logger.error("Failed to pause job", job_id=job_id, error=str(e))
        raise ValidationError(f"Failed to pause job: {str(e)}")


@workers_bp.post("/jobs/<job_id>/resume")
@openapi.tag("Workers")
@openapi.summary("Resume paused job")
@openapi.description("Resume a paused background job")
@openapi.parameter("job_id", str, "path", description="Job ID to resume")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Job resumed successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(422, description="Failed to resume job")
@require_auth
async def resume_job(request: Request, job_id: str):
    """
    Resume a paused job.

    Returns:
        200: Job resumed
        401: Not authenticated
    """
    try:
        worker_scheduler.resume_job(job_id)

        logger.info(
            "Job resumed via API",
            job_id=job_id,
            user_id=request.ctx.user["id"]
        )

        return response.json(
            {"message": f"Job {job_id} resumed successfully"},
            status=200,
        )

    except Exception as e:
        logger.error("Failed to resume job", job_id=job_id, error=str(e))
        raise ValidationError(f"Failed to resume job: {str(e)}")


@workers_bp.post("/jobs/<job_id>/trigger")
@openapi.tag("Workers")
@openapi.summary("Manually trigger job")
@openapi.description("Manually trigger a job to run immediately")
@openapi.parameter("job_id", str, "path", description="Job ID to trigger (monitor_positions, process_alerts)")
@openapi.secured("BearerAuth")
@openapi.response(200, description="Job triggered successfully")
@openapi.response(401, description="Not authenticated")
@openapi.response(404, description="Job not found or cannot be triggered manually")
@openapi.response(422, description="Failed to trigger job")
@require_auth
async def trigger_job_manually(request: Request, job_id: str):
    """
    Manually trigger a job to run immediately.

    Returns:
        200: Job triggered
        401: Not authenticated
        404: Job not found
    """
    try:
        from app.workers.monitor_worker import monitor_worker
        from app.workers.notifier_worker import notifier_worker

        # Map job IDs to worker functions
        job_map = {
            "monitor_positions": monitor_worker.run,
            "process_alerts": notifier_worker.run,
        }

        if job_id not in job_map:
            return response.json(
                {"error": f"Job {job_id} not found or cannot be triggered manually"},
                status=404
            )

        logger.info(
            "Manually triggering job",
            job_id=job_id,
            user_id=request.ctx.user["id"]
        )

        # Run the job
        result = await job_map[job_id]()

        return response.json(
            {
                "message": f"Job {job_id} triggered successfully",
                "result": result
            },
            status=200,
        )

    except Exception as e:
        logger.error("Failed to trigger job", job_id=job_id, error=str(e))
        raise ValidationError(f"Failed to trigger job: {str(e)}")
