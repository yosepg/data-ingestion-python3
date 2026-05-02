"""
SQLAlchemy ORM model for the Customer entity.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Numeric,
    String,
)
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

Base = declarative_base()


class Customer(Base):
    """Maps to the 'customers' table in customer_db."""

    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    account_balance: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        """Serialize the model instance to a plain dictionary."""
        return {
            "customer_id": self.customer_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "date_of_birth": (
                self.date_of_birth.isoformat() if self.date_of_birth else None
            ),
            "account_balance": (
                float(self.account_balance) if self.account_balance is not None else None
            ),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }

    def __repr__(self) -> str:
        return f"<Customer id={self.customer_id} email={self.email}>"
