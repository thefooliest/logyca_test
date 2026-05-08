from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    # PostgreSQL test
    
    POSTGRES_TEST_HOST: str = "localhost"
    POSTGRES_TEST_PORT: int = 5433
    POSTGRES_TEST_USER: str
    POSTGRES_TEST_PASSWORD: str
    POSTGRES_TEST_DB: str
    
    # Azure
    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_BLOB_CONTAINER: str = "sales-csv"
    AZURE_QUEUE_NAME: str = "sales-processing"

    # App
    LOG_LEVEL: str = "INFO"
    CHUNK_SIZE: int = 10000
    VISIBILITY_TIMEOUT: int = 1800  # 30 minutos

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()