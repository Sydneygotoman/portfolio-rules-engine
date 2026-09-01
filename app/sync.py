"""Pulls balances/prices from adapters and records the outcome. On a venue
failure, existing balances_snapshot rows for that venue are left untouched —
never silently refreshed with stale data mislabeled as current (spec §9) —
and a system_events row records the failure so the SYSTEM screen can show a
real "last successful sync" time distinct from "now"."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.exchange_adapters import ExchangeAdapter, has_trading_scope
from app.models import BalanceSnapshot, PriceRecord, SystemEvent
from app.price_service import generate_history

ALL_ASSETS = [
    "BTC", "ETH", "RENDER", "AERO", "EDU", "CSPR", "NAKA", "GFI",
    "SOL", "FET", "JTO", "PUMP", "SYS", "BRD", "MBOX", "VIDT",
]


def sync_venue(db: Session, adapter: ExchangeAdapter) -> None:
    venue = adapter.venue
    scopes = adapter.get_key_scopes()
    if has_trading_scope(scopes):
        db.add(
            SystemEvent(
                venue=venue,
                event_type="scope_refused",
                message=f"key scopes {scopes} include trade/withdraw capability — refusing to sync",
            )
        )
        db.commit()
        return

    now = datetime.utcnow()
    try:
        balances = adapter.get_balances()
        cash = adapter.get_cash_balance() if hasattr(adapter, "get_cash_balance") else 0.0
        for b in balances:
            db.add(BalanceSnapshot(venue=venue, asset=b.asset, quantity=b.quantity, as_of=now))
        db.add(BalanceSnapshot(venue=venue, asset="AUD", quantity=cash, as_of=now))
        db.add(SystemEvent(venue=venue, event_type="sync_ok", message=f"synced {len(balances)} balances"))
        db.commit()
    except Exception as exc:  # noqa: BLE001 — adapter-raised, message is not credential-bearing
        db.add(SystemEvent(venue=venue, event_type="sync_failed", message=str(exc)))
        db.commit()


def sync_prices(db: Session, adapter: ExchangeAdapter) -> None:
    now = datetime.utcnow()
    prices = adapter.get_prices(ALL_ASSETS)
    for asset, price in prices.items():
        db.add(PriceRecord(asset=asset, price_aud=price, as_of=now, source_venue=adapter.venue))
    db.commit()


def sync_all(db: Session, adapters: dict[str, ExchangeAdapter]) -> None:
    for adapter in adapters.values():
        sync_venue(db, adapter)
    # prices only need to come from one venue per asset; use whichever adapter
    # is healthy and has the widest coverage in this mock (swyftx first).
    for adapter in adapters.values():
        if adapter.health():
            sync_prices(db, adapter)
            break


def build_price_history(db: Session) -> dict[str, list[tuple]]:
    from sqlalchemy import select

    from app.models import PriceRecord as PR

    rows = db.execute(select(PR)).scalars().all()
    latest: dict[str, PR] = {}
    for row in rows:
        if row.asset not in latest or row.as_of > latest[row.asset].as_of:
            latest[row.asset] = row
    return {asset: generate_history(asset, row.price_aud) for asset, row in latest.items()}
