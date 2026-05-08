import json
import structlog
from azure.storage.queue.aio import QueueServiceClient
from azure.core.exceptions import ResourceExistsError

from core.config import settings

logger = structlog.get_logger()


class QueueService:
    def __init__(self, client:QueueServiceClient):
        self.client = client
        self.queue_name = settings.AZURE_QUEUE_NAME

    async def send(self, job_id: str, blob_name: str) -> None:
        async with self.client.get_queue_client(self.queue_name) as queue_client:
            message = json.dumps({"job_id": job_id, "blob_name": blob_name})
            await queue_client.send_message(
                message,
                visibility_timeout=0,
            )
        logger.info("message_sent", job_id=job_id, blob_name=blob_name)

    async def receive(self):
        async with self.client.get_queue_client(self.queue_name) as queue_client:
            messages = queue_client.receive_messages(
                max_messages=1,
                visibility_timeout=settings.VISIBILITY_TIMEOUT,
            )
            async for message in messages:
                return message
        return None

    async def delete(self, message) -> None:
        async with self.client.get_queue_client(self.queue_name) as queue_client:
            await queue_client.delete_message(message)
        logger.info("message_deleted", message_id=message.id)

    async def ensure_queue_exists(self) -> None:
        try:
            async with self.client.get_queue_client(self.queue_name) as queue_client:
                await queue_client.create_queue()
            logger.info("queue_created", queue=self.queue_name)
        except ResourceExistsError:
            logger.info("queue_already_exists", queue=self.queue_name)