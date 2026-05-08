import structlog
import asyncpg
import pandas as pd
from uuid import UUID

logger = structlog.get_logger()


class SalesRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def insert_batch(self, conn: asyncpg.Connection, job_id: str, df: pd.DataFrame) -> None:
        df = df.copy()
        df["job_id"] = str(job_id)

        records = list(
            df[["date", "product_id", "quantity", "price", "job_id"]]
            .itertuples(index=False, name=None)
        )
        print(records)
        await conn.copy_records_to_table(
            "sales",
            records=records,
            columns=["date", "product_id", "quantity", "price", "job_id"],
        )
        logger.info("batch_inserted", job_id=job_id, rows=len(records))

    async def save_errors(
        self,
        job_id: str,
        invalid_df: pd.DataFrame,
        byte_offset: int,
    ) -> None:
        invalid_df = invalid_df.copy()
        invalid_df["job_id"] = str(job_id)
        invalid_df["error_reason"] = "validation_failed"
        invalid_df["raw_content"] = invalid_df.apply(lambda row: str(row.to_dict()), axis=1)
        invalid_df["row_number"] = invalid_df.index

        records = list(
            invalid_df[["job_id", "row_number", "raw_content", "error_reason"]]
            .itertuples(index=False, name=None)
        )

        await self.pool.executemany(
            """
            INSERT INTO processing_errors (job_id, row_number, raw_content, error_reason)
            VALUES ($1, $2, $3, $4)
            """,
            records,
        )
        logger.info("errors_saved", job_id=job_id, count=len(records), byte_offset=byte_offset)