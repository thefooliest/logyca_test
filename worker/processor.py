import io
import csv
import asyncpg
import pandas as pd
import structlog
from uuid import UUID

from core.config import settings
from models.schemas import JobStatus
from services.blob import BlobService
from repository.jobs import JobRepository
from repository.sales import SalesRepository

logger = structlog.get_logger()

BYTE_CHUNK_SIZE = 1024 * 1024 * 5  # 5MB por bloque de lectura
CSV_COLUMNS = ["date", "product_id", "quantity", "price"]


async def process_file(
    job_id: str,
    blob_name: str,
    pool: asyncpg.Pool,
    blob_service: BlobService,
    job_repo: JobRepository,
) -> None:
    log = logger.bind(job_id=job_id, blob_name=blob_name)
    sales_repo = SalesRepository(pool)

    job = await job_repo.get_by_id(UUID(job_id))
    byte_offset = job["last_processed_byte"]
    is_resuming = byte_offset > 0

    await job_repo.update_status(UUID(job_id), JobStatus.PROCESSING)
    log.info("processing_started", byte_offset=byte_offset)

    has_errors = False
    total_rows_processed = 0
    leftover = b""

    try:
        async with blob_service.get_download_stream(blob_name, offset=byte_offset) as stream:
            while True:
                block = await stream.read(BYTE_CHUNK_SIZE)

                if not block:
                    if leftover:
                        _, chunk_has_errors = await _process_chunk(
                            chunk_bytes=leftover,
                            is_resuming=is_resuming,
                            byte_offset=byte_offset,
                            job_id=job_id,
                            pool=pool,
                            job_repo=job_repo,
                            sales_repo=sales_repo,
                            log=log,
                        )
                        if chunk_has_errors:
                            has_errors = True
                        byte_offset += len(leftover)
                        total_rows_processed += _count_rows(leftover)
                    break

                block = leftover + block
                last_newline = block.rfind(b"\n")

                if last_newline == -1:
                    leftover = block
                    continue

                chunk = block[:last_newline + 1]
                leftover = block[last_newline + 1:]

                rows_in_chunk, chunk_has_errors = await _process_chunk(
                    chunk_bytes=chunk,
                    is_resuming=is_resuming,
                    byte_offset=byte_offset,
                    job_id=job_id,
                    pool=pool,
                    job_repo=job_repo,
                    sales_repo=sales_repo,
                    log=log,
                )
                if chunk_has_errors:
                    has_errors = True
                byte_offset += len(chunk)
                total_rows_processed += rows_in_chunk
                is_resuming = False

        final_status = JobStatus.COMPLETED_WITH_ERRORS if has_errors else JobStatus.COMPLETED
        await job_repo.update_status(UUID(job_id), final_status)
        log.info("processing_completed", total_rows=total_rows_processed, status=final_status)

    except Exception as e:
        log.error("processing_error", error=str(e))
        await job_repo.update_status(UUID(job_id), JobStatus.FAILED)
        raise


async def _process_chunk(
    chunk_bytes: bytes,
    is_resuming: bool,
    byte_offset: int,
    job_id: str,
    pool: asyncpg.Pool,
    job_repo: JobRepository,
    sales_repo: SalesRepository,
    log,
) -> int:
    text = chunk_bytes.decode("utf-8")
    buffer = io.StringIO(text)

    if is_resuming:
        df = pd.read_csv(buffer, names=CSV_COLUMNS, header=None)
    else:
        df = pd.read_csv(buffer, header=0)
    df['date'] = pd.to_datetime(df['date'])
    valid, invalid = _validate(df)

    log.info(
        "chunk_parsed",
        byte_offset=byte_offset,
        valid_rows=len(valid),
        invalid_rows=len(invalid),
    )
    has_errors = not invalid.empty
    if has_errors:
        await sales_repo.save_errors(job_id, invalid, byte_offset)

    if not valid.empty:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await sales_repo.insert_batch(conn, job_id, valid)
                await job_repo.update_checkpoint(
                    job_id=UUID(job_id),
                    status=JobStatus.PROCESSING,
                    last_processed_byte=byte_offset + len(chunk_bytes),
                    conn=conn,
                )

    return len(df), has_errors


def _validate(df: pd.DataFrame):
    mask = (
        df["date"].notna() &
        df["product_id"].notna() &
        df["quantity"].notna() &
        df["price"].notna() &
        pd.to_numeric(df["quantity"], errors="coerce").gt(0) &
        pd.to_numeric(df["price"], errors="coerce").gt(0)
    )
    return df[mask].copy(), df[~mask].copy()


def _count_rows(chunk_bytes: bytes) -> int:
    return chunk_bytes.count(b"\n")