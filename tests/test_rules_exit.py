from datetime import date, timedelta

from app.rules_engine.exit_rules import hard_stop, ladder, relative_stop, thesis_invalidation, time_stop


def test_ladder_pass_below_3x(position_factory, metadata_factory):
    p = position_factory(price=2.99, metadata=metadata_factory(cost_basis=1.0))
    results = {r.rule_name: r for r in ladder(p)}
    assert results["ladder_3x"].status == "pass"


def test_ladder_breach_at_exactly_3x(position_factory, metadata_factory):
    p = position_factory(price=3.0, metadata=metadata_factory(cost_basis=1.0))
    results = {r.rule_name: r for r in ladder(p)}
    assert results["ladder_3x"].status == "breach"
    assert results["ladder_5x"].status == "pass"


def test_ladder_breach_at_10x(position_factory, metadata_factory):
    p = position_factory(price=10.0, metadata=metadata_factory(cost_basis=1.0))
    results = {r.rule_name: r for r in ladder(p)}
    assert results["ladder_3x"].status == "breach"
    assert results["ladder_5x"].status == "breach"
    assert results["ladder_10x"].status == "breach"


def test_hard_stop_pass_above_boundary(position_factory, metadata_factory):
    p = position_factory(price=0.6501, metadata=metadata_factory(cost_basis=1.0))
    assert hard_stop(p).status == "pass"


def test_hard_stop_breach_at_exactly_boundary(position_factory, metadata_factory):
    p = position_factory(price=0.65, metadata=metadata_factory(cost_basis=1.0))
    assert hard_stop(p).status == "breach"


def test_hard_stop_breach_below_boundary(position_factory, metadata_factory):
    p = position_factory(price=0.5, metadata=metadata_factory(cost_basis=1.0))
    assert hard_stop(p).status == "breach"


def test_time_stop_pass_well_before_deadline(position_factory, metadata_factory):
    entry = date(2025, 1, 1)
    p = position_factory(metadata=metadata_factory(entry_date=entry))
    result = time_stop(p, today=date(2025, 6, 1))
    assert result.status == "pass"


def test_time_stop_warning_within_14_days(position_factory, metadata_factory):
    entry = date(2025, 1, 1)
    p = position_factory(metadata=metadata_factory(entry_date=entry))
    result = time_stop(p, today=date(2025, 12, 25))  # 7 days before the 1-year deadline
    assert result.status == "warning"


def test_time_stop_breach_at_deadline(position_factory, metadata_factory):
    entry = date(2025, 1, 1)
    p = position_factory(metadata=metadata_factory(entry_date=entry))
    result = time_stop(p, today=date(2026, 1, 1))
    assert result.status == "breach"


def test_relative_stop_pass_above_boundary(position_factory, metadata_factory):
    p = position_factory(asset="ALT", metadata=metadata_factory(asset="ALT"))
    history = {
        "ALT": [(date(2025, 1, 1), 1.0), (date(2025, 4, 1), 0.90)],  # -10%
        "BTC": [(date(2025, 1, 1), 1.0), (date(2025, 4, 1), 1.19)],  # +19% -> underperformance -29%
    }
    result = relative_stop(p, history)
    assert result.status == "pass"


def test_relative_stop_breach_at_exactly_boundary(position_factory, metadata_factory):
    p = position_factory(asset="ALT", metadata=metadata_factory(asset="ALT"))
    history = {
        "ALT": [(date(2025, 1, 1), 1.0), (date(2025, 4, 1), 0.90)],  # -10%
        "BTC": [(date(2025, 1, 1), 1.0), (date(2025, 4, 1), 1.20)],  # +20% -> underperformance exactly -30%
    }
    result = relative_stop(p, history)
    assert result.status == "breach"


def test_relative_stop_exempts_btc_and_eth(metadata_factory, position_factory):
    p = position_factory(asset="BTC", metadata=metadata_factory(asset="BTC"))
    assert relative_stop(p, {"BTC": [(date(2025, 1, 1), 1.0)]}) is None


def test_thesis_invalidation_breach_when_flagged(position_factory, metadata_factory):
    p = position_factory(metadata=metadata_factory(thesis_invalidated=True))
    assert thesis_invalidation(p).status == "breach"


def test_thesis_invalidation_pass_when_not_flagged(position_factory, metadata_factory):
    p = position_factory(metadata=metadata_factory(thesis_invalidated=False))
    assert thesis_invalidation(p).status == "pass"
