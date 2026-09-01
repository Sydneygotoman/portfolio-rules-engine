"""Aggregation is by ASSET, never by venue — docs/ARCHITECTURE.md §4. This is
the one place that sums balances_snapshot across venues; the rules engine and
every dashboard screen must go through this, never re-sum per-venue rows
themselves."""

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BalanceSnapshot, PositionMetadata, PriceRecord


@dataclass
class AssetPosition:
    asset: str
    quantity: float
    price: float
    venues: dict[str, float]
    metadata: PositionMetadata | None
    price_as_of: datetime | None

    @property
    def value(self) -> float:
        return self.quantity * self.price


@dataclass
class PortfolioSnapshot:
    positions: list[AssetPosition]
    cash_by_venue: dict[str, float] = field(default_factory=dict)

    @property
    def cash_total(self) -> float:
        return sum(self.cash_by_venue.values())

    @property
    def total_value(self) -> float:
        return self.cash_total + sum(p.value for p in self.positions)

    def non_legacy(self) -> list[AssetPosition]:
        return [p for p in self.positions if not (p.metadata and p.metadata.classification == "legacy")]

    def legacy(self) -> list[AssetPosition]:
        return [p for p in self.positions if p.metadata and p.metadata.classification == "legacy"]


def _latest_by_key(rows, key_fn, time_fn):
    latest: dict = {}
    for row in rows:
        k = key_fn(row)
        if k not in latest or time_fn(row) > time_fn(latest[k]):
            latest[k] = row
    return latest


def build_snapshot(db: Session) -> PortfolioSnapshot:
    balance_rows = db.execute(select(BalanceSnapshot)).scalars().all()
    latest_balances = _latest_by_key(
        [r for r in balance_rows if r.asset != "AUD"],
        key_fn=lambda r: (r.venue, r.asset),
        time_fn=lambda r: r.as_of,
    )
    cash_rows = _latest_by_key(
        [r for r in balance_rows if r.asset == "AUD"],
        key_fn=lambda r: r.venue,
        time_fn=lambda r: r.as_of,
    )
    cash_by_venue = {venue: row.quantity for venue, row in cash_rows.items()}

    price_rows = db.execute(select(PriceRecord)).scalars().all()
    latest_prices = _latest_by_key(price_rows, key_fn=lambda r: r.asset, time_fn=lambda r: r.as_of)

    metadata_rows = db.execute(select(PositionMetadata)).scalars().all()
    metadata_by_asset = {m.asset: m for m in metadata_rows}

    by_asset: dict[str, dict[str, float]] = {}
    for (venue, asset), row in latest_balances.items():
        by_asset.setdefault(asset, {})[venue] = row.quantity

    positions = []
    for asset, venue_qty in by_asset.items():
        total_qty = sum(venue_qty.values())
        price_row = latest_prices.get(asset)
        positions.append(
            AssetPosition(
                asset=asset,
                quantity=total_qty,
                price=price_row.price_aud if price_row else 0.0,
                venues=venue_qty,
                metadata=metadata_by_asset.get(asset),
                price_as_of=price_row.as_of if price_row else None,
            )
        )
    positions.sort(key=lambda p: -p.value)
    return PortfolioSnapshot(positions=positions, cash_by_venue=cash_by_venue)
