from pydantic import BaseModel, UUID4
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"


class UploadResponse(BaseModel):
    job_id: UUID4
    status: JobStatus


class JobStatusResponse(BaseModel):
    job_id: UUID4
    status: JobStatus
    created_at: datetime
    updated_at: datetime