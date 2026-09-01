"""90-day price history store — built before the rules engine per
docs/ARCHITECTURE.md §2 ("the relative stop is the highest-value rule...
build the price history store first"). This mock implementation generates a
deterministic 90-day series ending at the asset's current price, driven by a
declared 90-day return, rather than fetching real OHLCV — there is no live
adapter to fetch from yet (see docs/CCXT_COVERAGE.md for what a real
implementation would use: fetchOHLCV, confirmed on all four CCXT venues)."""

import math
from datetime import date, timedelta

HISTORY_DAYS = 90

# Declared 90-day returns for the mock scenario. BTC is the benchmark every
# alt's relative-stop check is measured against.
_RETURN_90D: dict[str, float] = {
    "BTC": 0.18,
    "ETH": 0.12,
    "RENDER": -0.55,
    "SOL": 1.80,
    "FET": -0.20,  # -0.20 - 0.18 = -0.38 underperformance vs BTC -> relative stop breach
    "JTO": 0.05,
    "PUMP": 0.00,
}


def generate_history(asset: str, current_price: float, days: int = HISTORY_DAYS) -> list[tuple[date, float]]:
    """Deterministic — no randomness — so tests are reproducible."""
    return_90d = _RETURN_90D.get(asset, 0.0)
    start_price = current_price / (1 + return_90d) if (1 + return_90d) != 0 else current_price
    today = date.today()
    series = []
    for i in range(days, -1, -1):
        d = today - timedelta(days=i)
        progress = (days - i) / days
        base = start_price + (current_price - start_price) * progress
        wiggle = 1 + 0.01 * math.sin(i * 0.7)  # deterministic visual noise
        series.append((d, round(base * wiggle, 8)))
    series[-1] = (today, current_price)
    return series


def return_over(series: list[tuple[date, float]], days: int = HISTORY_DAYS) -> float:
    if len(series) < 2:
        return 0.0
    start_price = series[max(0, len(series) - 1 - days)][1]
    end_price = series[-1][1]
    if start_price == 0:
        return 0.0
    return (end_price - start_price) / start_price


def relative_performance(asset_series: list[tuple[date, float]], btc_series: list[tuple[date, float]]) -> float:
    """Asset's 90-day return minus BTC's 90-day return. <= -0.30 triggers the
    relative stop per docs/investment-rules-v1.md §4.2."""
    return return_over(asset_series) - return_over(btc_series)
