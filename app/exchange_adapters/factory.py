"""Picks a real adapter for a venue when its credentials are configured,
mock otherwise. Only Swyftx has a real adapter on this branch — Coinbase/
KuCoin/Gate/Crypto.com's CCXT-backed adapters are drafted on a separate,
still-untested branch (see the Stage 3 PR) and aren't wired in here yet."""

import os

from .mock import MockAdapter
from .swyftx import SwyftxAdapter


def get_adapters() -> dict:
    adapters = {}

    if os.environ.get("SWYFTX_API_KEY", "").strip():
        adapters["swyftx"] = SwyftxAdapter()
    else:
        adapters["swyftx"] = MockAdapter("swyftx")

    for venue in ("coinbase", "kucoin", "gate"):
        adapters[venue] = MockAdapter(venue)
    adapters["cryptocom"] = MockAdapter("cryptocom", healthy=False)

    return adapters
