-- Extensión para UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum para estado del job
CREATE TYPE job_status AS ENUM (
    'PENDING',
    'PROCESSING',
    'COMPLETED',
    'COMPLETED_WITH_ERRORS',
    'FAILED'
);

-- Tabla de jobs
CREATE TABLE jobs (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status               job_status NOT NULL DEFAULT 'PENDING',
    blob_name            TEXT NOT NULL,
    last_processed_byte  BIGINT NOT NULL DEFAULT 0,
    created_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Tabla de ventas particionada por fecha
CREATE TABLE sales (
    id         SERIAL,
    date       DATE NOT NULL,
    product_id INTEGER NOT NULL,
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    price      NUMERIC(10,2) NOT NULL CHECK (price > 0),
    total      NUMERIC(10,2) GENERATED ALWAYS AS (quantity * price) STORED,
    job_id     UUID NOT NULL REFERENCES jobs(id)
) PARTITION BY RANGE (date);

-- Partición default como red de seguridad
CREATE TABLE sales_default PARTITION OF sales DEFAULT;

-- Tabla de errores de procesamiento
CREATE TABLE processing_errors (
    id           SERIAL PRIMARY KEY,
    job_id       UUID NOT NULL REFERENCES jobs(id),
    row_number   INTEGER NOT NULL,
    raw_content  TEXT NOT NULL,
    error_reason TEXT NOT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Tabla de resumen diario (para n8n)
CREATE TABLE sales_daily_summary (
    id           SERIAL PRIMARY KEY,
    date         DATE NOT NULL UNIQUE,
    total_ventas NUMERIC(10,2) NOT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP NOT NULL DEFAULT NOW()
);