from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.aggregation import build_snapshot
from app.db import Base
from app.models import BalanceSnapshot, PriceRecord


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_multi_venue_asset_is_summed_not_duplicated(db_session):
    # AERO/EDU/NAKA/GFI/CSPR case from investment-rules-v1.md §2 — split across
    # Swyftx and KuCoin here, must appear as ONE aggregated position.
    now = datetime.utcnow()
    db_session.add(BalanceSnapshot(venue="swyftx", asset="AERO", quantity=100.0, as_of=now))
    db_session.add(BalanceSnapshot(venue="kucoin", asset="AERO", quantity=50.0, as_of=now))
    db_session.add(PriceRecord(asset="AERO", price_aud=1.0, as_of=now, source_venue="swyftx"))
    db_session.commit()

    snapshot = build_snapshot(db_session)

    aero_positions = [p for p in snapshot.positions if p.asset == "AERO"]
    assert len(aero_positions) == 1
    assert aero_positions[0].quantity == 150.0
    assert aero_positions[0].venues == {"swyftx": 100.0, "kucoin": 50.0}
    assert aero_positions[0].value == 150.0


def test_per_venue_view_available_without_a_second_code_path(db_session):
    now = datetime.utcnow()
    db_session.add(BalanceSnapshot(venue="swyftx", asset="EDU", quantity=900.0, as_of=now))
    db_session.add(BalanceSnapshot(venue="gate", asset="EDU", quantity=600.0, as_of=now))
    db_session.commit()

    snapshot = build_snapshot(db_session)
    edu = next(p for p in snapshot.positions if p.asset == "EDU")
    # the aggregate is authoritative, the per-venue breakdown rides along on it
    assert sum(edu.venues.values()) == edu.quantity


def test_cash_is_aggregated_across_venues(db_session):
    now = datetime.utcnow()
    db_session.add(BalanceSnapshot(venue="swyftx", asset="AUD", quantity=100.0, as_of=now))
    db_session.add(BalanceSnapshot(venue="coinbase", asset="AUD", quantity=50.0, as_of=now))
    db_session.commit()

    snapshot = build_snapshot(db_session)
    assert snapshot.cash_total == 150.0


def test_latest_balance_wins_when_a_venue_resyncs(db_session):
    from datetime import timedelta

    older = datetime.utcnow() - timedelta(hours=1)
    newer = datetime.utcnow()
    db_session.add(BalanceSnapshot(venue="swyftx", asset="BTC", quantity=0.001, as_of=older))
    db_session.add(BalanceSnapshot(venue="swyftx", asset="BTC", quantity=0.002, as_of=newer))
    db_session.commit()

    snapshot = build_snapshot(db_session)
    btc = next(p for p in snapshot.positions if p.asset == "BTC")
    assert btc.quantity == 0.002
