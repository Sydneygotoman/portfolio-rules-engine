# Portfolio Rules Engine

Read-only multi-exchange portfolio monitoring and rule enforcement tool.
Full spec: [`docs/rules-engine-build-spec.md`](docs/rules-engine-build-spec.md).
Thresholds/rules source of truth: [`docs/investment-rules-v1.md`](docs/investment-rules-v1.md).

## Status

**Stage 1 (audit)** is complete — see `docs/`. **No real exchange integration
exists yet.** Instead, this repo has a **mock-data build of the dashboard**:
the full data model, rules engine, and all eight dashboard screens, running
against mock exchange adapters (`app/exchange_adapters/mock.py`) seeded with
a scenario drawn from `docs/investment-rules-v1.md` itself (same tickers, same
RENDER cost-basis-mismatch example, same multi-venue duplicates). No real
credentials are used or needed to run it.

This exists because Stage 2 (the real Swyftx adapter) is blocked on API
details this environment couldn't verify — see the caveat below — while the
rules engine, data model, and UI don't depend on that being resolved. Real
exchange adapters (Stage 2/3 in `docs/rules-engine-build-spec.md`) are not
built yet; swapping mock adapters for real ones later should not require
changing anything above the `ExchangeAdapter` interface (`app/exchange_adapters/base.py`).

**Important caveat on the Stage 1 docs:** produced from a network-sandboxed
session that could not reach `docs.swyftx.com.au`, `docs.ccxt.com`, or most
exchange documentation domains directly. CCXT method support was confirmed
directly from CCXT's source on GitHub instead, and is solid. Swyftx's actual
API behavior and several venues' key-scope-introspection details are **not**
independently verified — see the `UNKNOWN` items in `docs/SWYFTX_API_AUDIT.md`
and `docs/SECURITY.md` §2 and §8. Those need to be re-checked from an
unrestricted network before a real Swyftx adapter is built, per the spec's
own rule: "Never guess an API. Mark unknowns and stop."

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
| Exchange adapters | **Mock only** — no live API calls anywhere in this repo |
| Notifications (spec §6) | Not built yet |
| Security startup scope-check enforcement | Implemented in `app/sync.py` (`has_trading_scope`), tested against mock scopes only — real per-venue introspection is still gated on `docs/SECURITY.md` §2/§8 |
