import asyncio
import os
import asyncpg
from pathlib import Path


async def run_migrations():
    retries = 5
    delay = 3

    for attempt in range(retries):
        try:
            conn = await asyncpg.connect(
                host=os.getenv("POSTGRES_HOST", "postgres"),
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                database=os.getenv("POSTGRES_DB"),
            )
            break
        except Exception as e:
            if attempt < retries - 1:
                print(f"Connection failed (attempt {attempt + 1}/{retries}): {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                print(f"Could not connect to PostgreSQL after {retries} attempts")
                raise

    try:
        migrations_dir = Path(__file__).parent / "migrations"
        migration_files = sorted(migrations_dir.glob("*.sql"))

        for migration_file in migration_files:
            print(f"Running migration: {migration_file.name}")
            sql = migration_file.read_text()
            await conn.execute(sql)
            print(f"✓ {migration_file.name} completed")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_migrations())