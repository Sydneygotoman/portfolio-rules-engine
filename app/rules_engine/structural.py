"""Structural rules — docs/investment-rules-v1.md §2. Operate on the whole,
already-aggregated-by-asset PortfolioSnapshot."""

from app.aggregation import PortfolioSnapshot
from .types import RuleResult

MAX_POSITIONS = 10
MIN_POSITION_WEIGHT = 0.05
MAX_POSITION_WEIGHT = 0.20
CASH_FLOOR = 0.20
CORE_MIN_WEIGHT = 0.50
MAX_CLUSTER_WEIGHT = 0.25
CORE_ASSETS = {"BTC", "ETH"}


def position_count(snapshot: PortfolioSnapshot) -> RuleResult:
    count = len(snapshot.non_legacy())
    status = "breach" if count > MAX_POSITIONS else "pass"
    return RuleResult(
        rule_name="position_count",
        status=status,
        computed_value=count,
        threshold=MAX_POSITIONS,
        reason=f"{count} non-legacy positions (limit {MAX_POSITIONS})",
    )


def position_sizing(snapshot: PortfolioSnapshot) -> list[RuleResult]:
    total = snapshot.total_value
    results = []
    if total <= 0:
        return results
    for p in snapshot.non_legacy():
        weight = p.value / total
        if weight > MAX_POSITION_WEIGHT:
            results.append(
                RuleResult(
                    rule_name="max_position_size",
                    status="breach",
                    computed_value=weight,
                    threshold=MAX_POSITION_WEIGHT,
                    reason=f"{p.asset} is {weight:.1%} of portfolio — trim to {MAX_POSITION_WEIGHT:.0%}",
                    asset=p.asset,
                )
            )
        elif weight < MIN_POSITION_WEIGHT:
            results.append(
                RuleResult(
                    rule_name="min_position_size",
                    status="warning",
                    computed_value=weight,
                    threshold=MIN_POSITION_WEIGHT,
                    reason=f"{p.asset} is {weight:.1%} of portfolio — below the {MIN_POSITION_WEIGHT:.0%} minimum",
                    asset=p.asset,
                )
            )
        else:
            results.append(
                RuleResult(
                    rule_name="position_sizing",
                    status="pass",
                    computed_value=weight,
                    threshold=MAX_POSITION_WEIGHT,
                    reason=f"{p.asset} is {weight:.1%} of portfolio",
                    asset=p.asset,
                )
            )
    return results


def cash_floor(snapshot: PortfolioSnapshot) -> RuleResult:
    total = snapshot.total_value
    weight = snapshot.cash_total / total if total > 0 else 0.0
    status = "breach" if weight < CASH_FLOOR else "pass"
    return RuleResult(
        rule_name="cash_floor",
        status=status,
        computed_value=weight,
        threshold=CASH_FLOOR,
        reason=f"cash is {weight:.1%} of portfolio (floor {CASH_FLOOR:.0%})",
    )


def core_allocation(snapshot: PortfolioSnapshot) -> RuleResult:
    total = snapshot.total_value
    core_value = sum(p.value for p in snapshot.positions if p.asset in CORE_ASSETS)
    weight = core_value / total if total > 0 else 0.0
    gap_dollars = max(0.0, CORE_MIN_WEIGHT * total - core_value)
    status = "breach" if weight < CORE_MIN_WEIGHT else "pass"
    return RuleResult(
        rule_name="core_allocation",
        status=status,
        computed_value=weight,
        threshold=CORE_MIN_WEIGHT,
        reason=f"BTC+ETH is {weight:.1%} of portfolio (target {CORE_MIN_WEIGHT:.0%}), gap ${gap_dollars:,.0f}",
    )


def narrative_cluster(snapshot: PortfolioSnapshot) -> list[RuleResult]:
    total = snapshot.total_value
    if total <= 0:
        return []
    by_cluster: dict[str, float] = {}
    for p in snapshot.non_legacy():
        cluster = p.metadata.narrative_cluster if p.metadata else None
        if not cluster:
            continue
        by_cluster.setdefault(cluster, 0.0)
        by_cluster[cluster] += p.value
    results = []
    for cluster, value in by_cluster.items():
        weight = value / total
        status = "breach" if weight > MAX_CLUSTER_WEIGHT else "pass"
        results.append(
            RuleResult(
                rule_name="narrative_cluster",
                status=status,
                computed_value=weight,
                threshold=MAX_CLUSTER_WEIGHT,
                reason=f"narrative cluster '{cluster}' is {weight:.1%} of portfolio (cap {MAX_CLUSTER_WEIGHT:.0%})",
                asset=cluster,
            )
        )
    return results


def evaluate_structural(snapshot: PortfolioSnapshot) -> list[RuleResult]:
    return [
        position_count(snapshot),
        *position_sizing(snapshot),
        cash_floor(snapshot),
        core_allocation(snapshot),
        *narrative_cluster(snapshot),
    ]
