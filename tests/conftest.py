import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.aggregation import AssetPosition
from app.models import PositionMetadata


def make_metadata(**overrides) -> PositionMetadata:
    defaults = dict(
        asset="TEST",
        cost_basis=1.0,
        venue_reported_cost_basis=None,
        entry_date=date(2025, 1, 1),
        thesis="test thesis",
        catalyst_name="test catalyst",
        catalyst_date=date(2025, 6, 1),
        invalidation="test invalidation",
        unlock_schedule_pct=5.0,
        liquidity_note="exitable same day",
        value_accrual="fee burn",
        fresh_cash_test=True,
        ladder_3x_price=3.0,
        ladder_5x_price=5.0,
        ladder_10x_price=10.0,
        hard_stop_price=0.65,
        time_stop_date=date(2026, 1, 1),
        narrative_cluster="test",
        classification="satellite",
        thesis_invalidated=False,
    )
    defaults.update(overrides)
    return PositionMetadata(**defaults)


def make_position(asset="TEST", quantity=100.0, price=1.0, venues=None, metadata="default") -> AssetPosition:
    if metadata == "default":
        metadata = make_metadata(asset=asset)
    return AssetPosition(
        asset=asset,
        quantity=quantity,
        price=price,
        venues=venues or {"mockvenue": quantity},
        metadata=metadata,
        price_as_of=None,
    )


@pytest.fixture
def metadata_factory():
    return make_metadata


@pytest.fixture
def position_factory():
    return make_position
