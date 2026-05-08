import asyncio
import json
import structlog
import asyncpg

from core.config import settings
from core.logging import setup_logging
from services.blob import BlobService
from services.queue import QueueService
from repository.jobs import JobRepository
from models.schemas import JobStatus
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.queue.aio import QueueServiceClient
from worker.processor import process_file

logger = structlog.get_logger()


async def main():
    setup_logging(settings.LOG_LEVEL)

    pool = await asyncpg.create_pool(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB,
        min_size=2,
        max_size=10,
    )
    blob_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
    queue_client = QueueServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
    blob_service = BlobService(blob_client)
    queue_service = QueueService(queue_client)
    job_repo = JobRepository(pool)

    await blob_service.ensure_container_exists()
    await queue_service.ensure_queue_exists()

    logger.info("worker_started")

    while True:
        try:
            message = await queue_service.receive()

            if message is None:
                await asyncio.sleep(5)
                continue

            body = json.loads(message.content)
            job_id = body["job_id"]
            blob_name = body["blob_name"]

            log = logger.bind(job_id=job_id, blob_name=blob_name)
            log.info("message_received")

            try:
                await process_file(
                    job_id=job_id,
                    blob_name=blob_name,
                    pool=pool,
                    blob_service=blob_service,
                    job_repo=job_repo,
                )
                await queue_service.delete(message)
                log.info("message_deleted")

            except Exception as e:
                log.error("processing_failed", error=str(e))

        except Exception as e:
            logger.error("worker_error", error=str(e))
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())