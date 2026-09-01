from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PositionMetadata(Base):
    """Locally-sourced, user-entered. Never overwritten by a sync — see
    docs/ARCHITECTURE.md §4. One row per asset (assets aggregate across venues)."""

    __tablename__ = "position_metadata"

    asset: Mapped[str] = mapped_column(String, primary_key=True)
    cost_basis: Mapped[float] = mapped_column(Float)
    venue_reported_cost_basis: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_date: Mapped[date] = mapped_column(Date)
    thesis: Mapped[str] = mapped_column(String)
    catalyst_name: Mapped[str] = mapped_column(String)
    catalyst_date: Mapped[date] = mapped_column(Date)
    invalidation: Mapped[str] = mapped_column(String)
    unlock_schedule_pct: Mapped[float] = mapped_column(Float)
    liquidity_note: Mapped[str] = mapped_column(String)
    value_accrual: Mapped[str] = mapped_column(String)
    fresh_cash_test: Mapped[bool] = mapped_column(Boolean)
    ladder_3x_price: Mapped[float] = mapped_column(Float)
    ladder_5x_price: Mapped[float] = mapped_column(Float)
    ladder_10x_price: Mapped[float] = mapped_column(Float)
    hard_stop_price: Mapped[float] = mapped_column(Float)
    time_stop_date: Mapped[date] = mapped_column(Date)
    narrative_cluster: Mapped[str] = mapped_column(String)
    classification: Mapped[str] = mapped_column(String)  # core | satellite | legacy
    thesis_invalidated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BalanceSnapshot(Base):
    """Live, exchange-sourced. Refreshed on sync, never hand-edited."""

    __tablename__ = "balances_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    venue: Mapped[str] = mapped_column(String)
    asset: Mapped[str] = mapped_column(String)
    quantity: Mapped[float] = mapped_column(Float)
    as_of: Mapped[datetime] = mapped_column(DateTime)


class PriceRecord(Base):
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset: Mapped[str] = mapped_column(String)
    price_aud: Mapped[float] = mapped_column(Float)
    as_of: Mapped[datetime] = mapped_column(DateTime)
    source_venue: Mapped[str] = mapped_column(String)


class RuleEvaluation(Base):
    __tablename__ = "rule_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_at: Mapped[datetime] = mapped_column(DateTime)
    rule_name: Mapped[str] = mapped_column(String)
    asset: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String)  # pass | breach | warning
    computed_value: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String)


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    asset: Mapped[str | None] = mapped_column(String, nullable=True)
    entry_text: Mapped[str] = mapped_column(String)


class SystemEvent(Base):
    __tablename__ = "system_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    venue: Mapped[str] = mapped_column(String)
    event_type: Mapped[str] = mapped_column(String)  # sync_ok | sync_failed | scope_refused
    message: Mapped[str] = mapped_column(String)
