# Cómo Ejecutar el Sistema

## Requisitos previos

- Docker
- Docker Compose
- Python 3.13 (solo para correr los tests localmente)

---

## Configuración inicial

### 1. Clonar el repositorio

```bash
git clone <repo>
cd logyca_test
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

El `.env.example` contiene todos los valores necesarios para desarrollo local. No necesitas modificar nada para correr el sistema con Docker Compose.

---

## Levantar el sistema

```bash
docker compose up --build
```

Esto levanta los servicios en este orden:

1. **PostgreSQL** — espera hasta estar saludable
2. **Azurite** — emulador local de Azure Storage
3. **Migrations** — crea tablas, particiones y funciones. Termina con `exited (0)`
4. **API** — disponible en `http://localhost:8000`
5. **Worker** — escucha la cola en segundo plano

Para verificar que todo está corriendo:

```bash
docker compose ps
```

Todos los servicios deben estar en estado `running` excepto `migrations` que estará `exited (0)`.

---

## Probar el sistema

### Subir un CSV

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@sample.csv"
```

Respuesta esperada:

```json
{
  "job_id": "uuid-aqui",
  "status": "PENDING"
}
```

### Consultar el estado de un job

```bash
curl http://localhost:8000/job/<job_id>
```

Respuesta esperada al completar:

```json
{
  "job_id": "uuid-aqui",
  "status": "COMPLETED",
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:01"
}
```

Los posibles estados son:

| Estado | Descripción |
|---|---|
| `PENDING` | El archivo fue recibido y está en cola |
| `PROCESSING` | El worker está procesando el archivo |
| `COMPLETED` | Procesamiento exitoso sin errores |
| `COMPLETED_WITH_ERRORS` | Procesamiento exitoso con algunas filas inválidas |
| `FAILED` | El procesamiento falló |

### Documentación interactiva de la API

FastAPI genera documentación automática disponible en:

```
http://localhost:8000/docs
```

---

## Detener el sistema

```bash
# Detener sin borrar datos
docker compose down

# Detener y borrar todos los datos de PostgreSQL
docker compose down -v
```

---

## Escalar workers

Para procesar múltiples archivos simultáneamente puedes levantar más réplicas del worker:

```bash
docker compose up --scale worker=3
```

---

## Ejecutar las pruebas

### Requisitos previos para tests

Las pruebas de integración requieren que `postgres_test` esté corriendo. La forma más simple es levantar solo ese servicio:

```bash
docker compose up postgres_test -d
```

### Instalar dependencias de desarrollo

```bash
pip install -r requirements.txt
```

### Correr todos los tests

```bash
pytest
```

### Correr solo los tests unitarios

Los tests unitarios no requieren ninguna dependencia externa:

```bash
pytest tests/test_validate.py -v
```

### Correr solo los tests de integración

```bash
pytest tests/test_repository.py tests/test_routes.py -v
```

### Correr con reporte de cobertura

```bash
pytest --cov=. --cov-report=term-missing
```

---

## Flujo de n8n

### Requisitos previos

- n8n corriendo localmente o en la nube
- Acceso a la misma base de datos PostgreSQL

### Importar el workflow

1. Abre n8n
2. Ve a **Workflows → Import from file**
3. Selecciona el archivo `n8n_workflow.json`

### Configurar credenciales

Crea una credencial llamada `PostgreSQL - Sales DB` en n8n con estos valores:

| Campo | Valor |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `sales_db` |
| User | valor de `POSTGRES_USER` en `.env` |
| Password | valor de `POSTGRES_PASSWORD` en `.env` |

### Activar el workflow

Una vez configuradas las credenciales, activa el workflow desde el toggle en la esquina superior derecha. Corre automáticamente cada noche a medianoche y:

1. Calcula el total de ventas por día de los jobs completados
2. Guarda o actualiza los resultados en `sales_daily_summary`
3. Crea la partición de la tabla `sales` para el día siguiente

---

## Estructura del proyecto

```
logyca_test/
├── api/
│   ├── main.py                  # FastAPI app y lifespan
│   └── routes/
│       ├── upload.py            # POST /upload
│       └── jobs.py              # GET /job/{job_id}
├── core/
│   ├── config.py                # Variables de entorno con pydantic-settings
│   └── logging.py               # Configuración de structlog
├── db/
│   └── migrations/
│       ├── 001_initial.sql      # Tablas principales
│       ├── 002_partitions.sql   # Función y particiones del año
│       └── 003_create_partition_next_day.sql  # Función para n8n
├── models/
│   └── schemas.py               # Pydantic models para la API
├── repository/
│   ├── jobs.py                  # CRUD de jobs
│   └── sales.py                 # Inserts de sales y errores
├── services/
│   ├── blob.py                  # Azure Blob Storage
│   └── queue.py                 # Azure Queue Storage
├── worker/
│   ├── consumer.py              # Loop principal, escucha la cola
│   └── processor.py             # Lógica de chunks, validación, checkpointing
├── tests/
│   ├── conftest.py              # Fixtures de pytest
│   ├── test_validate.py         # Tests unitarios de validación
│   ├── test_repository.py       # Tests de integración del repository
│   └── test_routes.py           # Tests de integración de la API
├── sample.csv                   # CSV de ejemplo para pruebas
├── n8n_workflow.json            # Export del workflow de n8n
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pytest.ini
├── .env.example
└── README.md
```