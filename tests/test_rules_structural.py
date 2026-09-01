from app.aggregation import PortfolioSnapshot
from app.rules_engine.structural import (
    cash_floor,
    core_allocation,
    narrative_cluster,
    position_count,
    position_sizing,
)


def test_position_count_pass_at_boundary(position_factory):
    positions = [position_factory(asset=f"A{i}", price=1, quantity=1) for i in range(10)]
    snapshot = PortfolioSnapshot(positions=positions, cash_by_venue={"v": 100})
    result = position_count(snapshot)
    assert result.status == "pass"


def test_position_count_breach_above_boundary(position_factory):
    positions = [position_factory(asset=f"A{i}", price=1, quantity=1) for i in range(11)]
    snapshot = PortfolioSnapshot(positions=positions, cash_by_venue={"v": 100})
    result = position_count(snapshot)
    assert result.status == "breach"


def test_position_count_ignores_legacy(position_factory, metadata_factory):
    non_legacy = [position_factory(asset=f"A{i}", price=1, quantity=1) for i in range(10)]
    legacy = [
        position_factory(asset=f"L{i}", price=1, quantity=1, metadata=metadata_factory(classification="legacy"))
        for i in range(50)
    ]
    snapshot = PortfolioSnapshot(positions=non_legacy + legacy, cash_by_venue={"v": 100})
    assert position_count(snapshot).status == "pass"


def _weight_snapshot(weight: float, cash_weight: float = 0.3):
    # total = 1000; one position at `weight`, rest is a second filler position, plus cash.
    total = 1000.0
    cash = total * cash_weight
    target = total * weight
    filler = total - cash - target
    from tests.conftest import make_position

    positions = [make_position(asset="TARGET", price=1, quantity=target)]
    if filler > 0:
        positions.append(make_position(asset="FILLER", price=1, quantity=filler))
    return PortfolioSnapshot(positions=positions, cash_by_venue={"v": cash})


def test_min_position_size_pass_at_exactly_5pct():
    snapshot = _weight_snapshot(0.05, cash_weight=0.30)
    results = position_sizing(snapshot)
    target = next(r for r in results if r.asset == "TARGET")
    assert target.status == "pass"


def test_min_position_size_warning_below_5pct():
    snapshot = _weight_snapshot(0.04, cash_weight=0.30)
    results = position_sizing(snapshot)
    target = next(r for r in results if r.asset == "TARGET")
    assert target.status == "warning"


def test_max_position_size_pass_at_exactly_20pct():
    snapshot = _weight_snapshot(0.20, cash_weight=0.30)
    results = position_sizing(snapshot)
    target = next(r for r in results if r.asset == "TARGET")
    assert target.status == "pass"


def test_max_position_size_breach_above_20pct():
    snapshot = _weight_snapshot(0.21, cash_weight=0.30)
    results = position_sizing(snapshot)
    target = next(r for r in results if r.asset == "TARGET")
    assert target.status == "breach"


def test_cash_floor_pass_at_exactly_20pct(position_factory):
    snapshot = PortfolioSnapshot(positions=[position_factory(price=1, quantity=800)], cash_by_venue={"v": 200})
    assert cash_floor(snapshot).status == "pass"


def test_cash_floor_breach_below_20pct(position_factory):
    snapshot = PortfolioSnapshot(positions=[position_factory(price=1, quantity=810)], cash_by_venue={"v": 190})
    assert cash_floor(snapshot).status == "breach"


def test_core_allocation_pass_at_exactly_50pct(position_factory):
    btc = position_factory(asset="BTC", price=1, quantity=500)
    other = position_factory(asset="OTHER", price=1, quantity=500)
    snapshot = PortfolioSnapshot(positions=[btc, other], cash_by_venue={})
    assert core_allocation(snapshot).status == "pass"


def test_core_allocation_breach_below_50pct(position_factory):
    btc = position_factory(asset="BTC", price=1, quantity=499)
    other = position_factory(asset="OTHER", price=1, quantity=501)
    snapshot = PortfolioSnapshot(positions=[btc, other], cash_by_venue={})
    result = core_allocation(snapshot)
    assert result.status == "breach"
    assert "gap" in result.reason


def test_narrative_cluster_breach_above_25pct(position_factory, metadata_factory):
    sol = position_factory(asset="SOL", price=1, quantity=200, metadata=metadata_factory(asset="SOL", narrative_cluster="solana"))
    jto = position_factory(asset="JTO", price=1, quantity=100, metadata=metadata_factory(asset="JTO", narrative_cluster="solana"))
    filler = position_factory(asset="FILLER", price=1, quantity=700)
    snapshot = PortfolioSnapshot(positions=[sol, jto, filler], cash_by_venue={})
    result = next(r for r in narrative_cluster(snapshot) if r.asset == "solana")
    assert result.status == "breach"


def test_narrative_cluster_pass_at_exactly_25pct(position_factory, metadata_factory):
    sol = position_factory(asset="SOL", price=1, quantity=250, metadata=metadata_factory(asset="SOL", narrative_cluster="solana"))
    filler = position_factory(asset="FILLER", price=1, quantity=750)
    snapshot = PortfolioSnapshot(positions=[sol, filler], cash_by_venue={})
    result = next(r for r in narrative_cluster(snapshot) if r.asset == "solana")
    assert result.status == "pass"
