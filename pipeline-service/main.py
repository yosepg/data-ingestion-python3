"""
Pipeline Service – FastAPI application.

Endpoints:
    POST /api/ingest                       Trigger full ingestion from mock-server
    GET  /api/customers?page=&limit=       Paginated customer list from DB
    GET  /api/customers/{id}               Single customer from DB
    GET  /api/health                       Health check
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import check_db_connection, get_db, init_db
from models.customer import Customer
from services.ingestion import ingest_customers

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise DB tables before accepting requests."""
    logger.info("Starting pipeline-service …")
    init_db()
    yield
    logger.info("Shutting down pipeline-service …")


app = FastAPI(
    title="Data Ingestion Pipeline Service",
    description="Fetches customer data from the mock-server and stores it in PostgreSQL.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """Return service health, including DB connectivity."""
    db_ok = check_db_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "pipeline-service",
        "database": "connected" if db_ok else "unreachable",
    }


@app.post("/api/ingest", tags=["Ingestion"])
def trigger_ingestion(db: Session = Depends(get_db)):
    """
    Fetch ALL customer data from the Flask mock-server (auto-pagination),
    then upsert into PostgreSQL.

    Returns:
        {"status": "success", "records_processed": <n>}
    """
    try:
        result = ingest_customers(db)
        return JSONResponse(status_code=200, content=result)
    except Exception as exc:
        logger.exception("Ingestion failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc


@app.get("/api/customers", tags=["Customers"])
def list_customers(
    page: int = Query(default=1, ge=1, description="1-based page number"),
    limit: int = Query(default=10, ge=1, le=100, description="Records per page"),
    db: Session = Depends(get_db),
):
    """
    Return a paginated list of customers stored in the database.

    Query params:
        page  (int, default 1)
        limit (int, default 10, max 100)
    """
    total: int = db.query(Customer).count()
    offset: int = (page - 1) * limit
    customers = (
        db.query(Customer)
        .order_by(Customer.customer_id)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "data": [c.to_dict() for c in customers],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total else 0,
    }


@app.get("/api/customers/{customer_id}", tags=["Customers"])
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    """
    Return a single customer by customer_id.
    Raises HTTP 404 if the customer does not exist.
    """
    customer: Customer | None = (
        db.query(Customer).filter(Customer.customer_id == customer_id).first()
    )
    if customer is None:
        raise HTTPException(
            status_code=404,
            detail=f"Customer '{customer_id}' not found.",
        )
    return {"data": customer.to_dict()}
