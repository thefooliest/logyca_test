from contextlib import asynccontextmanager
import asyncpg
from fastapi import FastAPI
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.queue.aio import QueueServiceClient
from core.logging import setup_logging
from core.config import settings
from api.routes import upload, jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.LOG_LEVEL)
    
    app.state.db_pool = await asyncpg.create_pool(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB,
        min_size=2,
        max_size=10,
    )
    app.state.azure_blob_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
    app.state.azure_queue_client = QueueServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
    
    yield
    
    await app.state.db_pool.close()
    await app.state.azure_blob_client.close()
    await app.state.azure_queue_client.close()

app = FastAPI(
    title="Sales CSV Processor",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(upload.router)
app.include_router(jobs.router)