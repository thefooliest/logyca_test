import structlog
from fastapi import UploadFile
from azure.storage.blob.aio import BlobServiceClient, StorageStreamDownloader
from azure.core.exceptions import ResourceExistsError
from core.config import settings

logger = structlog.get_logger()

CHUNK_SIZE = 1024 * 1024  # 1MB


class BlobService:
    def __init__(self, client:BlobServiceClient):
        self.client = client
        self.container = settings.AZURE_BLOB_CONTAINER

    async def upload(self, blob_name: str, file: UploadFile) -> None:
        async def chunk_generator():
            while chunk := await file.read(CHUNK_SIZE):
                yield chunk

        async with self.client.get_blob_client(
            container=self.container,
            blob=blob_name,
        ) as blob_client:
            await blob_client.upload_blob(
                data=chunk_generator(),
                overwrite=True,
            )

        logger.info("blob_upload_completed", blob_name=blob_name)

    def get_download_stream(self, blob_name: str, offset: int = 0):
        return _BlobDownloadContext(self.client, self.container, blob_name, offset=offset)

    async def ensure_container_exists(self) -> None:
        try:
            async with self.client.get_container_client(self.container) as container_client:
                await container_client.create_container()
            logger.info("container_created", container=self.container)
        except ResourceExistsError:
            logger.info("container_already_exists", container=self.container)


class _BlobDownloadContext:
    def __init__(
        self,
        client: BlobServiceClient,
        container: str,
        blob_name: str,
        offset: int = 0,
    ):
        self.client = client
        self.container = container
        self.blob_name = blob_name
        self.offset = offset
        self._blob_client = None

    async def __aenter__(self) -> StorageStreamDownloader:
        self._blob_client = self.client.get_blob_client(
            container=self.container,
            blob=self.blob_name,
        )
        stream = await self._blob_client.download_blob(
            offset=self.offset if self.offset > 0 else None
        )
        return stream

    async def __aexit__(self, *args) -> None:
        if self._blob_client:
            await self._blob_client.close()