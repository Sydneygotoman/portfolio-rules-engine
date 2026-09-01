"""Cost basis is always the user-entered figure (docs/ARCHITECTURE.md §4) —
never the exchange-reported one. This only flags a material mismatch for
display; it never corrects or overwrites the entered value."""

from app.aggregation import AssetPosition
from .types import RuleResult

MATERIAL_MISMATCH_PCT = 0.15


def detect_mismatch(position: AssetPosition) -> RuleResult | None:
    meta = position.metadata
    if not meta or meta.venue_reported_cost_basis is None or meta.cost_basis <= 0:
        return None
    diff_pct = abs(meta.venue_reported_cost_basis - meta.cost_basis) / meta.cost_basis
    status = "warning" if diff_pct > MATERIAL_MISMATCH_PCT else "pass"
    return RuleResult(
        rule_name="cost_basis_mismatch",
        status=status,
        computed_value=diff_pct,
        threshold=MATERIAL_MISMATCH_PCT,
        reason=(
            f"{position.asset}: entered cost basis ${meta.cost_basis:g} differs from venue-reported "
            f"${meta.venue_reported_cost_basis:g} by {diff_pct:.0%} — using entered figure"
            if status == "warning"
            else f"{position.asset}: entered and venue-reported cost basis agree within {MATERIAL_MISMATCH_PCT:.0%}"
        ),
        asset=position.asset,
    )
