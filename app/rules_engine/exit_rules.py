"""Exit rules — docs/investment-rules-v1.md §4. Per-position; the relative
stop additionally needs 90-day price history for the asset and for BTC."""

from datetime import date

from app.aggregation import AssetPosition
from app.price_service import relative_performance
from .types import RuleResult

HARD_STOP_PCT = -0.35
RELATIVE_STOP_PCT = -0.30
TIME_STOP_DAYS = 365
TIME_STOP_WARNING_DAYS = 14
LADDER_LEVELS = [(3.0, "3x", "sell 33%"), (5.0, "5x", "sell 25%"), (10.0, "10x", "sell 25%")]


def ladder(position: AssetPosition) -> list[RuleResult]:
    meta = position.metadata
    if not meta or meta.cost_basis <= 0:
        return []
    multiple = position.price / meta.cost_basis
    results = []
    for level, label, action in LADDER_LEVELS:
        status = "breach" if multiple >= level else "pass"
        results.append(
            RuleResult(
                rule_name=f"ladder_{label}",
                status=status,
                computed_value=multiple,
                threshold=level,
                reason=(
                    f"{position.asset} is at {multiple:.1f}x entry — {action}"
                    if status == "breach"
                    else f"{position.asset} is at {multiple:.1f}x entry (next ladder {level}x)"
                ),
                asset=position.asset,
            )
        )
    return results


def hard_stop(position: AssetPosition) -> RuleResult | None:
    meta = position.metadata
    if not meta or meta.cost_basis <= 0:
        return None
    pct = (position.price - meta.cost_basis) / meta.cost_basis
    status = "breach" if pct <= HARD_STOP_PCT else "pass"
    return RuleResult(
        rule_name="hard_stop",
        status=status,
        computed_value=pct,
        threshold=HARD_STOP_PCT,
        reason=f"{position.asset} is {pct:.1%} from entry (hard stop at {HARD_STOP_PCT:.0%})",
        asset=position.asset,
    )


def time_stop(position: AssetPosition, today: date | None = None) -> RuleResult | None:
    meta = position.metadata
    if not meta:
        return None
    today = today or date.today()
    deadline = date(meta.entry_date.year + 1, meta.entry_date.month, meta.entry_date.day)
    days_remaining = (deadline - today).days
    if days_remaining <= 0:
        status = "breach"
    elif days_remaining <= TIME_STOP_WARNING_DAYS:
        status = "warning"
    else:
        status = "pass"
    return RuleResult(
        rule_name="time_stop",
        status=status,
        computed_value=days_remaining,
        threshold=0,
        reason=(
            f"{position.asset} time stop reached ({deadline.isoformat()}) — exit regardless of price"
            if status == "breach"
            else f"{position.asset} time stop in {days_remaining} days ({deadline.isoformat()})"
        ),
        asset=position.asset,
    )


def relative_stop(
    position: AssetPosition,
    price_history: dict[str, list[tuple[date, float]]],
) -> RuleResult | None:
    if position.asset in ("BTC", "ETH"):
        return None  # core assets are exempt — spec §3.1
    asset_series = price_history.get(position.asset)
    btc_series = price_history.get("BTC")
    if not asset_series or not btc_series:
        return None
    underperformance = round(relative_performance(asset_series, btc_series), 6)
    status = "breach" if underperformance <= RELATIVE_STOP_PCT else "pass"
    return RuleResult(
        rule_name="relative_stop",
        status=status,
        computed_value=underperformance,
        threshold=RELATIVE_STOP_PCT,
        reason=(
            f"{position.asset} has underperformed BTC by {abs(underperformance):.1%} over 90 days — mandatory review"
            if status == "breach"
            else f"{position.asset} vs BTC over 90 days: {underperformance:+.1%}"
        ),
        asset=position.asset,
    )


def thesis_invalidation(position: AssetPosition) -> RuleResult | None:
    meta = position.metadata
    if not meta:
        return None
    status = "breach" if meta.thesis_invalidated else "pass"
    return RuleResult(
        rule_name="thesis_invalidation",
        status=status,
        computed_value=1.0 if meta.thesis_invalidated else 0.0,
        threshold=0.0,
        reason=(
            f"{position.asset} thesis flagged invalid — exit immediately, price irrelevant"
            if status == "breach"
            else f"{position.asset} thesis holds"
        ),
        asset=position.asset,
    )


def evaluate_exit_rules(
    position: AssetPosition,
    price_history: dict[str, list[tuple[date, float]]],
    today: date | None = None,
) -> list[RuleResult]:
    if position.metadata and position.metadata.classification == "legacy":
        return []
    results = [*ladder(position)]
    for r in (
        hard_stop(position),
        time_stop(position, today),
        relative_stop(position, price_history),
        thesis_invalidation(position),
    ):
        if r is not None:
            results.append(r)
    return results
