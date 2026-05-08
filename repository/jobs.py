import structlog
from uuid import UUID
from asyncpg import Pool

from models.schemas import JobStatus

logger = structlog.get_logger()


class JobRepository:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def create(self, job_id: UUID, blob_name: str) -> None:
        await self.pool.execute(
            """
            INSERT INTO jobs (id, status, blob_name)
            VALUES ($1, $2, $3)
            """,
            job_id,
            JobStatus.PENDING.value,
            blob_name,
        )

    async def get_by_id(self, job_id: UUID) -> dict | None:
        row = await self.pool.fetchrow(
            """
            SELECT id, status, last_processed_byte, created_at, updated_at
            FROM jobs
            WHERE id = $1
            """,
            job_id,
        )
        return dict(row) if row else None

    async def update_status(self, job_id: UUID, status: JobStatus) -> None:
        await self.pool.execute(
            """
            UPDATE jobs
            SET status = $1, updated_at = NOW()
            WHERE id = $2
            """,
            status.value,
            job_id,
        )

    async def update_checkpoint(
        self,
        job_id: UUID,
        status: JobStatus,
        last_processed_byte: int,
        conn,
    ) -> None:
        await conn.execute(
            """
            UPDATE jobs
            SET status = $1,
                last_processed_byte = $2,
                updated_at = NOW()
            WHERE id = $3
            """,
            status.value,
            last_processed_byte,
            job_id,
        )