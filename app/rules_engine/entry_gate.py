"""Entry gate — docs/investment-rules-v1.md §3.2 and §3.1. A save-time
validation on position_metadata, not a scheduled rule (docs/ARCHITECTURE.md
§6): it belongs to the write path, not the evaluator loop."""

from datetime import date

from app.price_service import relative_performance
from .types import RuleResult

REQUIRED_CHECKLIST_FIELDS = [
    "value_accrual",
    "catalyst_name",
    "catalyst_date",
    "invalidation",
    "unlock_schedule_pct",
    "liquidity_note",
    "fresh_cash_test",
]

CORE_ASSETS = {"BTC", "ETH"}


def missing_checklist_fields(data: dict) -> list[str]:
    """Empty fields block the save — this is the point of the tool. `False` is
    a valid value for fresh_cash_test and `0` a valid value for
    unlock_schedule_pct, so only None / empty-string counts as missing."""
    missing = []
    for field in REQUIRED_CHECKLIST_FIELDS:
        value = data.get(field)
        if value is None or value == "":
            missing.append(field)
    return missing


def check_alt_outperformance(
    asset: str,
    price_history: dict[str, list[tuple[date, float]]],
) -> RuleResult | None:
    """Warn, never block, per spec §3.1 — BTC/ETH are exempt."""
    if asset in CORE_ASSETS:
        return None
    asset_series = price_history.get(asset)
    btc_series = price_history.get("BTC")
    if not asset_series or not btc_series:
        return None
    underperformance = relative_performance(asset_series, btc_series)
    status = "warning" if underperformance < 0 else "pass"
    return RuleResult(
        rule_name="entry_alt_outperformance",
        status=status,
        computed_value=underperformance,
        threshold=0.0,
        reason=(
            f"{asset} is underperforming BTC by {abs(underperformance):.1%} over the trailing 90 days at entry"
            if status == "warning"
            else f"{asset} is outperforming BTC by {underperformance:.1%} over the trailing 90 days"
        ),
        asset=asset,
    )
