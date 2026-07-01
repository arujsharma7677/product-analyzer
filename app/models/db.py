"""
SQLAlchemy ORM models mapping the existing prepaid-credit schema
(see migrations/001_credit_system.sql).

These map tables that ALREADY exist in the database — SQLAlchemy does not
create them. In particular:

  - user_usage.total_tokens is a GENERATED column (input + output), mapped as
    Computed(...) — never inserted, always read back.
  - user_usage.credits_deducted is a plain column the app writes; usage
    deduction happens in code (see credit_service.log_usage_batch), not via a
    trigger (removed in migrations/002_deduction_in_code.sql).
  - Inserting an admin_recharge_log row still fires fn_after_recharge.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Computed,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    """public.users — only the columns this service reads.

    The real PK is users.id (uuid), but we resolve everything by the
    canonical users.number business key, so we map that as the identity.
    This model is read-only here (signup/login go through the Supabase SDK).
    """
    __tablename__ = "users"

    number: Mapped[int] = mapped_column(Integer, primary_key=True)
    auth_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))


class UserCredits(Base):
    __tablename__ = "user_credits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_number: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.number", ondelete="CASCADE"), unique=True
    )
    total_credits_purchased: Mapped[float] = mapped_column(Numeric(12, 2), server_default="0")
    credits_used: Mapped[float] = mapped_column(Numeric(12, 2), server_default="0")
    credits_balance: Mapped[float] = mapped_column(Numeric(12, 2), server_default="0")
    last_recharged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdminRechargeLog(Base):
    __tablename__ = "admin_recharge_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_number: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.number", ondelete="CASCADE")
    )
    recharge_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    credits_granted: Mapped[float] = mapped_column(Numeric(12, 2))
    payment_reference: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    recharged_by: Mapped[str] = mapped_column(Text, server_default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserUsage(Base):
    __tablename__ = "user_usage"
    # eager_defaults => emit RETURNING so the generated columns
    # (total_tokens, credits_deducted) come back on INSERT.
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_number: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.number", ondelete="CASCADE")
    )
    type: Mapped[str] = mapped_column(Text)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    # total_tokens stays a DB-generated column (not money-related).
    total_tokens: Mapped[int] = mapped_column(
        Integer, Computed("(input_tokens + output_tokens)", persisted=True)
    )
    # credits_deducted is now written by the app (flat 6500 per row); the DB
    # no longer computes it or deducts credits — the service does both.
    credits_deducted: Mapped[float] = mapped_column(Numeric(12, 2), server_default="6500")
    catalog_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    catalog_name: Mapped[str | None] = mapped_column(Text)
    model_used: Mapped[str | None] = mapped_column(Text, server_default="claude-sonnet-4-6")
    status: Mapped[str | None] = mapped_column(Text, server_default="success")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_number: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.number", ondelete="CASCADE")
    )
    transaction_type: Mapped[str] = mapped_column(Text)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    balance_before: Mapped[float] = mapped_column(Numeric(12, 2))
    balance_after: Mapped[float] = mapped_column(Numeric(12, 2))
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reference_type: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
