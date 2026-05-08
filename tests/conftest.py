import pytest
import asyncpg
import asyncio
from httpx import AsyncClient, ASGITransport
from pathlib import Path

from api.main import app
from core.config import settings


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_pool():
    pool = await asyncpg.create_pool(
        host=settings.POSTGRES_TEST_HOST,
        port=settings.POSTGRES_TEST_PORT,
        user=settings.POSTGRES_TEST_USER,
        password=settings.POSTGRES_TEST_PASSWORD,
        database=settings.POSTGRES_TEST_DB,
        min_size=2,
        max_size=5,
    )
    yield pool
    await pool.close()


@pytest.fixture(scope="session")
async def run_migrations(db_pool):
    migrations_dir = Path(__file__).parent.parent / "db" / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))

    async with db_pool.acquire() as conn:
        for migration_file in migration_files:
            sql = migration_file.read_text()
            await conn.execute(sql)

    yield

    async with db_pool.acquire() as conn:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")


@pytest.fixture(scope="function")
async def clean_db(db_pool, run_migrations):
    yield
    async with db_pool.acquire() as conn:
        await conn.execute("TRUNCATE jobs, processing_errors, sales_daily_summary RESTART IDENTITY CASCADE")


@pytest.fixture(scope="session")
async def api_client(db_pool, run_migrations):
    app.state.db_pool = db_pool
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client