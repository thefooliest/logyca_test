import uuid
import structlog
from fastapi import APIRouter, UploadFile, File, HTTPException, Request

from models.schemas import UploadResponse, JobStatus
from services.blob import BlobService
from services.queue import QueueService
from repository.jobs import JobRepository

logger = structlog.get_logger()

router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_csv(request: Request, file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    job_id = uuid.uuid4()
    blob_name = f"{job_id}/{file.filename}"
    log = logger.bind(job_id=str(job_id), blob_name=blob_name)

    pool = request.app.state.db_pool
    blob_client= request.app.state.azure_blob_client
    queue_client= request.app.state.azure_queue_client

    blob_service = BlobService(blob_client)
    queue_service = QueueService(queue_client)
    job_repo = JobRepository(pool)

    try:
        log.info("upload_started")
        await blob_service.upload(blob_name, file)
        log.info("blob_uploaded")
    except Exception as e:
        log.error("blob_upload_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    try:
        await job_repo.create(job_id, blob_name)
        log.info("job_created")
    except Exception as e:
        log.error("job_creation_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create job")

    try:
        await queue_service.send(str(job_id), blob_name)
        log.info("message_queued")
    except Exception as e:
        log.error("queue_send_failed", error=str(e))
        await job_repo.update_status(job_id, JobStatus.FAILED)
        raise HTTPException(status_code=500, detail="Failed to queue processing job")

    return UploadResponse(job_id=job_id, status=JobStatus.PENDING)