# Data Ingestion Pipeline — Python 3 / Docker Compose

A three-service MVP that demonstrates a real-world data ingestion pipeline:

```
Flask mock-server (port 5000)  →  FastAPI pipeline-service (port 8000)  →  PostgreSQL (port 5432)
```

---

## Project Structure

```
data-ingestion-python3/
├── docker-compose.yml
├── README.md
├── postgres/
│   └── init.sql                    # DDL run on first container start
├── mock-server/                    # Flask — customer data source
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py
│   └── data/
│       └── customers.json          # 22 sample customers
└── pipeline-service/               # FastAPI — ingestion pipeline
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py                     # FastAPI app + routes
    ├── database.py                 # SQLAlchemy engine & session
    ├── models/
    │   └── customer.py             # ORM model
    └── services/
        └── ingestion.py            # Fetch + upsert + dlt pipeline
```

---

## Services

### 1. `mock-server` — Flask (port 5000)

Serves 22 pre-loaded customers from `data/customers.json`.

| Method | Endpoint                  | Description                         |
|--------|---------------------------|-------------------------------------|
| GET    | `/api/health`             | Health check                        |
| GET    | `/api/customers`          | Paginated list (`page`, `limit`)    |
| GET    | `/api/customers/<id>`     | Single customer or **404**          |

**Response format:**
```json
{
  "data": [...],
  "total": 22,
  "page": 1,
  "limit": 10,
  "total_pages": 3
}
```

---

### 2. `pipeline-service` — FastAPI (port 8000)

Fetches data from the mock-server and upserts it into PostgreSQL.
Interactive docs: **http://localhost:8000/docs**

| Method | Endpoint                       | Description                               |
|--------|--------------------------------|-------------------------------------------|
| GET    | `/api/health`                  | Health check + DB connectivity            |
| POST   | `/api/ingest`                  | Trigger full ingestion (auto-paginated)   |
| GET    | `/api/customers`               | Paginated customers from DB               |
| GET    | `/api/customers/{id}`          | Single customer from DB or **404**        |

**Ingest response:**
```json
{ "status": "success", "records_processed": 22 }
```

---

### 3. `postgres` — PostgreSQL 15 (port 5432)

| Setting          | Value          |
|------------------|----------------|
| Database         | `customer_db`  |
| User             | `postgres`     |
| Password         | `password`     |
| Connection URL   | `postgresql://postgres:password@localhost:5432/customer_db` |

**Schema — `customers` table:**

| Column           | Type             | Notes        |
|------------------|------------------|--------------|
| `customer_id`    | VARCHAR(50)      | Primary key  |
| `first_name`     | VARCHAR(100)     | NOT NULL     |
| `last_name`      | VARCHAR(100)     | NOT NULL     |
| `email`          | VARCHAR(255)     | NOT NULL     |
| `phone`          | VARCHAR(20)      |              |
| `address`        | VARCHAR(255)     |              |
| `date_of_birth`  | DATE             |              |
| `account_balance`| DECIMAL(15,2)    |              |
| `created_at`     | TIMESTAMP        |              |

---

## Quick Start

### Prerequisites
- Docker Dekstop / Colima / Rancher
- Docker Compose v2 (bundled with Docker Desktop)

### 1 — Build and start all services

```bash
docker compose up --build
```

### 2 — Trigger data ingestion

```bash
curl -X POST http://localhost:8000/api/ingest
```

Expected response:
```json
{"status": "success", "records_processed": 22}
```

### 3 — Query customers via the pipeline service (from DB)

```bash
# Paginated list
curl "http://localhost:8000/api/customers?page=1&limit=5"

# Single customer
curl http://localhost:8000/api/customers/CUST-001
```

### 4 — Query the mock-server directly

```bash
# Paginated
curl "http://localhost:5000/api/customers?page=2&limit=5"

# Single customer
curl http://localhost:5000/api/customers/CUST-010

# Health
curl http://localhost:5000/api/health
```

### 5 — Interactive API docs (FastAPI)

Open **http://localhost:8000/docs** in your browser.

### 6 — Connect to PostgreSQL directly

```bash
docker exec -it postgres psql -U postgres -d customer_db -c "SELECT * FROM customers LIMIT 5;"
```

---

## Stopping

```bash
# Stop and remove containers (data volume is preserved)
docker compose down

# Stop and also remove the data volume
docker compose down -v
```

---

## Environment Variables

All configurable via `docker-compose.yml` → `pipeline-service.environment`:

| Variable          | Default                                           | Description                    |
|-------------------|---------------------------------------------------|--------------------------------|
| `DATABASE_URL`    | `postgresql://postgres:password@postgres:5432/customer_db` | PostgreSQL connection string |
| `MOCK_SERVER_URL` | `http://mock-server:5000`                         | Base URL of the Flask server   |
| `INGEST_PAGE_SIZE`| `10`                                              | Records per page during fetch  |
| `HTTP_TIMEOUT`    | `30`                                              | HTTP client timeout (seconds)  |

---

## Ingestion Pipeline Details

The `POST /api/ingest` endpoint:

1. **Auto-paginates** through the Flask API until all records are fetched.
2. **Upserts** records into PostgreSQL using `INSERT … ON CONFLICT DO UPDATE` — safe to call multiple times.
3. **Also runs a `dlt` pipeline** (`write_disposition="merge"`) for data lineage tracking and future extensibility.
