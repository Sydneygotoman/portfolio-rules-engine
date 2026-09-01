"""Mock adapters. No network calls, ever — this is what the test suite and the
demo dashboard run against instead of live exchanges (spec §9: "never hit live
APIs in tests"). Seed data below mirrors the scenario described in
docs/investment-rules-v1.md (same tickers, same cost-basis-mismatch example)
so the dashboard demonstrates real rule breaches rather than placeholder noise.
"""

from .base import Balance, ExchangeAdapter

# venue -> {asset: quantity}
_BALANCES: dict[str, dict[str, float]] = {
    "swyftx": {
        "AUD": 900.0,
        "BTC": 0.003,
        "ETH": 0.10,
        "RENDER": 2050.0,  # cost basis mismatch case: spec's own RENDER example
        "AERO": 140.0,
        "EDU": 900.0,
        "CSPR": 3000.0,
    },
    "coinbase": {
        "AUD": 300.0,
        "BTC": 0.00167,
    },
    "kucoin": {
        "AUD": 150.0,
        "AERO": 110.0,
        "NAKA": 800.0,
        "CSPR": 2200.0,
        # worthless-asset candidates named in investment-rules-v1.md §9
        "SYS": 4000.0,
        "BRD": 1500.0,
        "MBOX": 900.0,
        "VIDT": 2000.0,
    },
    "gate": {
        "AUD": 120.0,
        "EDU": 600.0,
        "GFI": 950.0,
        "SOL": 8.5,
        "FET": 900.0,
        "JTO": 380.0,
    },
    "cryptocom": {
        # deliberately holds a slice of a multi-venue asset (NAKA/GFI) plus one
        # single-venue asset (PUMP) — this venue is flagged unhealthy below, so
        # the SYSTEM screen and dashboard demonstrate a real partial-outage:
        # NAKA/GFI still show (reduced) via kucoin/gate, PUMP disappears
        # entirely until the sync recovers, and none of it is silently shown
        # as current (see docs/SECURITY.md §6 and app/sync.py).
        "AUD": 90.0,
        "NAKA": 650.0,
        "GFI": 700.0,
        "PUMP": 12000.0,
    },
}

# asset -> current price in AUD. Deliberately chosen so several rules breach:
# RENDER is well below the entered cost basis (hard stop), FET has lagged BTC,
# SOL has run to a ladder trigger, the dust-tier legacy assets are near zero.
_PRICES: dict[str, float] = {
    "BTC": 148000.0,
    "ETH": 3840.0,
    "RENDER": 0.25,
    "AERO": 0.72,
    "EDU": 0.29,
    "CSPR": 0.021,
    "NAKA": 0.031,
    "GFI": 0.018,
    "SOL": 235.0,
    "FET": 0.42,
    "JTO": 1.85,
    "PUMP": 0.0028,
    "SYS": 0.045,
    "BRD": 0.006,
    "MBOX": 0.031,
    "VIDT": 0.0009,
}


class MockAdapter(ExchangeAdapter):
    """One instance per venue. `scopes` and `healthy` are constructor knobs so
    tests and the demo SYSTEM screen can simulate a mis-scoped key or a venue
    outage without touching the interface shape."""

    def __init__(self, venue: str, scopes: list[str] | None = None, healthy: bool = True):
        self.venue = venue
        self._scopes = scopes if scopes is not None else ["general_read_only"]
        self._healthy = healthy

    def get_balances(self) -> list[Balance]:
        if not self._healthy:
            raise ConnectionError(f"{self.venue}: mock sync failure")
        return [
            Balance(venue=self.venue, asset=asset, quantity=qty)
            for asset, qty in _BALANCES.get(self.venue, {}).items()
            if asset != "AUD"
        ]

    def get_cash_balance(self) -> float:
        if not self._healthy:
            raise ConnectionError(f"{self.venue}: mock sync failure")
        return _BALANCES.get(self.venue, {}).get("AUD", 0.0)

    def get_prices(self, assets: list[str]) -> dict[str, float]:
        return {a: _PRICES[a] for a in assets if a in _PRICES}

    def get_key_scopes(self) -> list[str]:
        return self._scopes

    def health(self) -> bool:
        return self._healthy


TRADE_SCOPED_MARKERS = {"trade", "withdraw", "transfer", "spot", "margin", "futures"}


def has_trading_scope(scopes: list[str]) -> bool:
    return any(marker in scope.lower() for scope in scopes for marker in TRADE_SCOPED_MARKERS)


def all_mock_adapters() -> dict[str, MockAdapter]:
    """The five venues, one flagged unhealthy (Crypto.com) so the SYSTEM screen
    has a real stale-data example to show, per spec §9's staleness requirement."""
    return {
        "swyftx": MockAdapter("swyftx"),
        "coinbase": MockAdapter("coinbase"),
        "kucoin": MockAdapter("kucoin"),
        "gate": MockAdapter("gate"),
        "cryptocom": MockAdapter("cryptocom", healthy=False),
    }
