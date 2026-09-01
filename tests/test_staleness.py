import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.exchange_adapters import MockAdapter, has_trading_scope
from app.models import BalanceSnapshot, SystemEvent
from app.sync import sync_venue


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_healthy_venue_syncs_and_records_ok(db_session):
    adapter = MockAdapter("swyftx")
    sync_venue(db_session, adapter)

    balances = db_session.execute(select(BalanceSnapshot).where(BalanceSnapshot.venue == "swyftx")).scalars().all()
    assert len(balances) > 0
    events = db_session.execute(select(SystemEvent).where(SystemEvent.venue == "swyftx")).scalars().all()
    assert any(e.event_type == "sync_ok" for e in events)


def test_failed_venue_does_not_write_fresh_looking_balances(db_session):
    # a prior successful sync exists...
    good_adapter = MockAdapter("cryptocom", healthy=True)
    sync_venue(db_session, good_adapter)
    balances_before = db_session.execute(
        select(BalanceSnapshot).where(BalanceSnapshot.venue == "cryptocom")
    ).scalars().all()
    assert len(balances_before) > 0

    # ...then the venue goes down. A failed sync must not add new rows that
    # would read as "current" — the old rows (now stale) are what's left.
    bad_adapter = MockAdapter("cryptocom", healthy=False)
    sync_venue(db_session, bad_adapter)

    balances_after = db_session.execute(
        select(BalanceSnapshot).where(BalanceSnapshot.venue == "cryptocom")
    ).scalars().all()
    assert len(balances_after) == len(balances_before)  # nothing new written

    events = db_session.execute(select(SystemEvent).where(SystemEvent.venue == "cryptocom")).scalars().all()
    assert any(e.event_type == "sync_failed" for e in events)


def test_trading_scoped_key_is_detected():
    assert has_trading_scope(["general_read_only"]) is False
    assert has_trading_scope(["General", "Trade"]) is True
    assert has_trading_scope(["view"]) is False
    assert has_trading_scope(["trade"]) is True
    assert has_trading_scope(["can_withdraw"]) is True


def test_startup_refuses_to_sync_a_trading_scoped_key(db_session):
    adapter = MockAdapter("kucoin", scopes=["General", "Trade"])
    sync_venue(db_session, adapter)

    balances = db_session.execute(select(BalanceSnapshot).where(BalanceSnapshot.venue == "kucoin")).scalars().all()
    assert balances == []  # refused before ever calling get_balances

    events = db_session.execute(select(SystemEvent).where(SystemEvent.venue == "kucoin")).scalars().all()
    assert any(e.event_type == "scope_refused" for e in events)
