from datetime import date

from app.aggregation import PortfolioSnapshot
from .cost_basis import detect_mismatch
from .exit_rules import evaluate_exit_rules
from .structural import evaluate_structural
from .types import RuleResult


def evaluate_all(
    snapshot: PortfolioSnapshot,
    price_history: dict[str, list[tuple[date, float]]],
    today: date | None = None,
) -> list[RuleResult]:
    results = evaluate_structural(snapshot)
    for position in snapshot.positions:
        results.extend(evaluate_exit_rules(position, price_history, today))
        mismatch = detect_mismatch(position)
        if mismatch is not None:
            results.append(mismatch)
    return results


def breaches_only(results: list[RuleResult]) -> list[RuleResult]:
    severity = {"breach": 0, "warning": 1, "pass": 2}
    return sorted(
        (r for r in results if r.status in ("breach", "warning")),
        key=lambda r: severity[r.status],
    )
