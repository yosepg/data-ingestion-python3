"""
Ingestion service: fetches customer data from the Flask mock-server with
auto-pagination and upserts records into PostgreSQL using dlt.
"""

import logging
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generator

import dlt
import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from models.customer import Customer

logger = logging.getLogger(__name__)

MOCK_SERVER_URL: str = os.environ.get(
    "MOCK_SERVER_URL", "http://mock-server:5000"
)
PAGE_SIZE: int = int(os.environ.get("INGEST_PAGE_SIZE", "10"))
HTTP_TIMEOUT: float = float(os.environ.get("HTTP_TIMEOUT", "30"))


# ---------------------------------------------------------------------------
# Helper: fetch all pages from the Flask mock-server
# ---------------------------------------------------------------------------

def fetch_all_customers() -> list[dict]:
    """
    Fetch every customer from the Flask mock-server, handling pagination
    automatically.

    Returns a flat list of customer dicts.
    """
    all_records: list[dict] = []
    page = 1

    with httpx.Client(base_url=MOCK_SERVER_URL, timeout=HTTP_TIMEOUT) as client:
        while True:
            logger.info("Fetching page %d (limit=%d) from mock-server …", page, PAGE_SIZE)
            resp = client.get(
                "/api/customers",
                params={"page": page, "limit": PAGE_SIZE},
            )
            resp.raise_for_status()
            payload: dict = resp.json()

            records: list[dict] = payload.get("data", [])
            all_records.extend(records)

            total: int = payload.get("total", 0)

            logger.info(
                "Page %d: received %d records (total seen: %d / %d)",
                page, len(records), len(all_records), total,
            )

            if len(all_records) >= total or not records:
                break

            page += 1

    logger.info("Finished fetching: %d records total.", len(all_records))
    return all_records

# ---------------------------------------------------------------------------
# Helpers: parsing and transformation
# ---------------------------------------------------------------------------

def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        # Expected format from JSON: "YYYY-MM-DD"
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        logger.error("Invalid date format: %s", value)
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        # Handles "YYYY-MM-DDTHH:MM:SSZ" or "YYYY-MM-DDTHH:MM:SS+HH:MM"
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        logger.error("Invalid datetime format: %s", value)
        return None


# ---------------------------------------------------------------------------
# dlt resource + pipeline
# ---------------------------------------------------------------------------

@dlt.resource(
    name="customers",
    write_disposition="merge",
    primary_key="customer_id",
    columns=[
        {"name": "customer_id", "data_type": "text", "primary_key": True},
        {"name": "first_name", "data_type": "text", "nullable": False},
        {"name": "last_name", "data_type": "text", "nullable": False},
        {"name": "email", "data_type": "text", "nullable": False},
        {"name": "date_of_birth", "data_type": "date", "nullable": True},
        {"name": "account_balance", "data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
        {"name": "created_at", "data_type": "timestamp", "nullable": True},
    ]
)
def customers_resource(records: list[dict]) -> Generator[dict, None, None]:
    """
    dlt resource that emits one row per customer.
    Parses strings into Python types for correct DB mapping.
    """
    for r in records:
        # Transform into Python objects so dlt uses correct SQL types
        row = {
            "customer_id": r["customer_id"],
            "first_name": r["first_name"],
            "last_name": r["last_name"],
            "email": r["email"],
            "phone": r.get("phone"),
            "address": r.get("address"),
            "date_of_birth": _parse_date(r.get("date_of_birth")),
            "account_balance": (
                Decimal(str(r["account_balance"]))
                if r.get("account_balance") is not None
                else None
            ),
            "created_at": _parse_datetime(r.get("created_at")),
        }
        yield row


def run_dlt_pipeline(records: list[dict]) -> int:
    """
    Run the dlt pipeline to load *records* into PostgreSQL.
    Returns the number of rows processed.
    """
    database_url: str = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:password@postgres:5432/customer_db",
    )

    pipeline = dlt.pipeline(
        pipeline_name="customer_ingestion_v2",
        destination=dlt.destinations.postgres(database_url),
        dataset_name="public",  # schema = public → table = customers
    )
    pipeline.drop()

    load_info = pipeline.run(customers_resource(records))
    logger.info("dlt load info: %s", load_info)
    return len(records)




def upsert_customers_sqlalchemy(db: Session, records: list[dict]) -> int:
    """
    Upsert a list of customer dicts into PostgreSQL using SQLAlchemy's
    PostgreSQL INSERT … ON CONFLICT DO UPDATE.

    Returns the number of rows processed.
    """
    if not records:
        return 0

    rows = []
    for r in records:
        rows.append({
            "customer_id": r["customer_id"],
            "first_name": r["first_name"],
            "last_name": r["last_name"],
            "email": r["email"],
            "phone": r.get("phone"),
            "address": r.get("address"),
            "date_of_birth": _parse_date(r.get("date_of_birth")),
            "account_balance": (
                Decimal(str(r["account_balance"]))
                if r.get("account_balance") is not None
                else None
            ),
            "created_at": _parse_datetime(r.get("created_at")),
        })

    stmt = pg_insert(Customer).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["customer_id"],
        set_={
            "first_name": stmt.excluded.first_name,
            "last_name": stmt.excluded.last_name,
            "email": stmt.excluded.email,
            "phone": stmt.excluded.phone,
            "address": stmt.excluded.address,
            "date_of_birth": stmt.excluded.date_of_birth,
            "account_balance": stmt.excluded.account_balance,
            "created_at": stmt.excluded.created_at,
        },
    )

    db.execute(stmt)
    db.commit()
    logger.info("Upserted %d customers via SQLAlchemy.", len(rows))
    return len(rows)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def ingest_customers(db: Session) -> dict:
    """
    Orchestrates the full ingestion pipeline:
      1. Fetch all pages from Flask mock-server (auto-paginated).
      2. Ingest into PostgreSQL using dlt library (handles upsert/merge).

    Returns a summary dict.
    """
    records = fetch_all_customers()

    if not records:
        return {"status": "success", "records_processed": 0, "message": "No records fetched."}

    try:
        processed = run_dlt_pipeline(records)
        return {"status": "success", "records_processed": processed}
    except Exception as exc:
        logger.exception("dlt pipeline run failed: %s", exc)
        raise exc
