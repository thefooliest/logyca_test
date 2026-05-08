import structlog
from fastapi import APIRouter, HTTPException, Request
from uuid import UUID

from models.schemas import JobStatusResponse
from repository.jobs import JobRepository

logger = structlog.get_logger()

router = APIRouter()


@router.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: UUID, request: Request):
    log = logger.bind(job_id=str(job_id))
    pool = request.app.state.db_pool
    job_repo = JobRepository(pool)

    try:
        job = await job_repo.get_by_id(job_id)
    except Exception as e:
        log.error("job_fetch_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to fetch job status")

    if job is None:
        log.warning("job_not_found")
        raise HTTPException(status_code=404, detail="Job not found")

    log.info("job_status_fetched", status=job["status"])
    return JobStatusResponse(
        job_id=job["id"],
        status=job["status"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
    )