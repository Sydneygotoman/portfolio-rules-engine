# Portfolio Rules Engine

Read-only multi-exchange portfolio monitoring and rule enforcement tool.
Full spec: [`docs/rules-engine-build-spec.md`](docs/rules-engine-build-spec.md).
Thresholds/rules source of truth: [`docs/investment-rules-v1.md`](docs/investment-rules-v1.md).

## Status

**Stage 1 (audit)** is complete — see `docs/`. The dashboard (data model, rules
engine, all eight screens) is real and fully tested against mock exchange data
(`app/exchange_adapters/mock.py`), seeded from `docs/investment-rules-v1.md`'s
own scenario.

**Swyftx** (the largest holding) now has a real adapter — `app/exchange_adapters/swyftx.py` —
built from a shape confirmed by two independent implementations (see
`docs/SWYFTX_API_AUDIT.md`), including a live 401/403 from Swyftx's real API.
**It has not yet seen a real successful (200) response end-to-end** — set
`SWYFTX_API_KEY` (and, after confirming in the Swyftx UI that the key is
read-only, `SWYFTX_ATTESTED_READONLY=true`) to actually exercise it; without
those set, the app runs on Swyftx mock data exactly as before. Coinbase/
KuCoin/Gate's CCXT-backed adapters are drafted on a separate branch, also
untested — Crypto.com's is not started. Swapping any adapter for a real one
shouldn't require changing anything above the `ExchangeAdapter` interface
(`app/exchange_adapters/base.py`).

**Important caveat, still true for the other four venues:** produced from a
network-sandboxed session that cannot reach exchange API hosts at all — a raw
HTTPS request to `api.coinbase.com` gets a 403 at the proxy, same class of
block as the docs sites. CCXT method support for Coinbase/KuCoin/Gate/
Crypto.com is confirmed from CCXT's own source, which is solid for what
methods exist, but none of those four adapters have been exercised against a
live account either. Test all of them against real **read-only** keys, on a
network that can actually reach these hosts, before trusting any of it.

## Running the mock dashboard

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/overview. The database (`portfolio.db`,
git-ignored) is created and seeded automatically on first run. Delete it to
reset to the seeded demo state.

Run the test suite (rule boundaries, multi-venue aggregation, cost-basis
mismatch, staleness/outage handling, entry-gate validation, trading-scope
refusal — per `docs/rules-engine-build-spec.md` §9):

```
pytest
```

## What's real vs. mock right now

| Layer | Status |
|---|---|
| Data model, aggregation, rules engine, entry gate | Real logic, fully tested |
| Dashboard (all 8 screens from spec §5) | Real, running against the mock data below |
| Exchange adapters | Swyftx: real, unverified end-to-end (needs a real key + attestation to activate; mock otherwise). Coinbase/KuCoin/Gate/Crypto.com: mock only |
| Notifications (spec §6) | Not built yet |
| Security startup scope-check enforcement | Implemented in `app/sync.py` (`has_trading_scope`), tested against mock scopes only — real per-venue introspection is still gated on `docs/SECURITY.md` §2/§8 |
