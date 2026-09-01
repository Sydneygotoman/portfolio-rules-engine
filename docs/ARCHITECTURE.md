# Architecture — Portfolio Rules Engine

Stage 1 output. No application code exists yet — this document describes what
Stages 2–10 will build, per `rules-engine-build-spec.md`. Read that file and
`investment-rules-v1.md` first; this document doesn't restate the rules, only
how the system is structured to evaluate them.

## 1. Shape of the system

A single-user, local, read-only monitoring tool. It pulls balances and prices
from five exchanges on a schedule, joins them with locally-entered position
metadata (thesis, entry, stops, ladders), evaluates a fixed rule set against
the result, and surfaces breaches on a dashboard and via notification. It holds
no capability to place an order, move funds, or otherwise act — see
`SECURITY.md` §1 for how that's enforced structurally, not just by policy.

```
/exchange-adapters   ExchangeAdapter interface; ccxt wrapper (4 venues) + custom Swyftx adapter
/price-service       90-day price history store; BTC-relative performance calc
/rules-engine        rule definitions + evaluator, pure functions over a portfolio snapshot
/api                 FastAPI backend — read endpoints + the position-metadata CRUD
/frontend            dashboard (dark, sections per spec §5)
/database            SQLite (single-user local; see §5 below)
/notifications       email/Telegram dispatch on rule-evaluation triggers
/tests
/docs
```

## 2. Data flow

```
                    ┌─────────────────────┐
                    │  Scheduler (cron /   │
                    │  run-on-demand — see │
                    │  open decision #1)   │
                    └──────────┬───────────┘
                               │
                 ┌─────────────┴─────────────┐
                 ▼                            ▼
       ┌───────────────────┐        ┌──────────────────┐
       │ ExchangeAdapter ×5 │        │ position_metadata │  (user-entered,
       │ get_balances()     │        │ (thesis, entry,   │   never overwritten
       │ get_prices()       │        │  stops, ladders)  │   by a sync)
       └─────────┬──────────┘        └─────────┬─────────┘
                 │                              │
                 ▼                              │
       balances_snapshot, prices                │
       (per-venue, keyed by venue+asset)        │
                 │                              │
                 └──────────────┬───────────────┘
                                ▼
                 Aggregation: sum by ASSET across venues
                 (spec §3 — AERO/EDU/NAKA/GFI/CSPR case)
                                │
                                ▼
                    ┌───────────────────────┐
                    │   price-service        │
                    │   90-day history,      │
                    │   BTC-relative perf     │
                    └───────────┬────────────┘
                                ▼
                    ┌───────────────────────┐
                    │    rules-engine        │
                    │  evaluates every rule  │
                    │  in investment-rules-  │
                    │  v1.md against the     │
                    │  aggregated snapshot   │
                    └───────────┬────────────┘
                                ▼
                    rule_evaluations, breaches
                                │
                 ┌──────────────┴──────────────┐
                 ▼                              ▼
            dashboard (api → frontend)   notifications (spec §6 triggers)
```

The critical ordering constraint from the spec: **price-service comes before
rules-engine**, because the relative stop (underperformance vs. BTC over 90
days) is called out as "the highest-value rule in the system" and every other
exit rule can be evaluated without price history, but that one can't. Stage 5
exists before Stage 6 for exactly this reason — don't reorder it.

## 3. Adapter interface

```
get_balances()      -> list[Balance]     # per venue, per asset, quantity
get_prices(assets)  -> dict[asset, price]
get_key_scopes()    -> list[scope]       # for startup verification, see SECURITY.md §2
health()            -> status
```

Four methods, no more. This interface is itself a security control (see
`SECURITY.md` §1) — it's the reason a CCXT dependency that exposes
`createOrder` can't reach the rest of the system: nothing calls it. Adding a
fifth method to this interface should require the same review scrutiny as
touching `SECURITY.md` itself.

Two adapter families:
- **CCXT-backed** (Coinbase, KuCoin, Gate, Crypto.com) — one thin wrapper class
  per venue translating the interface above into the corresponding CCXT calls.
  See `CCXT_COVERAGE.md` for confirmed method support and required credentials
  per venue.
- **Custom** (Swyftx) — CCXT doesn't support it. See `SWYFTX_API_AUDIT.md`;
  this adapter cannot be started until that document's open items are resolved,
  per the build spec's "do not invent endpoints" rule.

## 4. Data model

Exchanges know balances; they do not know thesis. This split is the central
design fact (spec §3) and drives the table boundary below.

**Live, exchange-sourced (refreshed on sync, never hand-edited):**
- `balances_snapshot` — venue, asset, quantity, as-of timestamp
- `prices` — asset, price, as-of timestamp, source venue
- `system_events` — sync attempts, per-venue success/failure, staleness state

**Local, user-sourced (persisted, never overwritten by a sync):**
- `position_metadata` — cost basis, entry date, thesis, catalyst + date window,
  invalidation condition, ladder levels (3x/5x/10x), hard stop price, time stop
  date, narrative cluster tag, classification (`core`/`satellite`/`legacy`)

**Derived:**
- `positions` — the aggregation join: sum of `balances_snapshot` by asset across
  all venues, joined to `position_metadata` by asset. This is what the rules
  engine and the dashboard's POSITIONS screen read from — never a per-venue row.
- `rule_evaluations` — one row per rule per evaluation run, holding computed
  value, threshold, and result (`pass`/`breach`/`warning`)
- `breaches` — the subset of `rule_evaluations` currently in `breach` or
  `warning` state; what the dashboard's BREACHES screen reads
- `journal_entries` — weekly entries, position notes, rule amendment log
  (spec §8 of `investment-rules-v1.md`)

**Cost basis is never read from an exchange as authoritative** (spec §3) —
Swyftx records transfer-date market price for transferred-in coins, not actual
purchase price; KuCoin and Gate don't track it at all. `position_metadata.cost_basis`
is the only value the rules engine uses; if a venue reports a materially
different figure, that's a flagged discrepancy, not a correction.

**Aggregation is by asset, never by venue**, for every weight/allocation rule.
A per-venue breakdown is a display detail on the POSITIONS screen, not a second
code path — there should be exactly one aggregation function, and the per-venue
view calls it and then also shows the pre-aggregation rows, rather than
computing weights twice.

## 5. Storage

SQLite, per spec §8 — single-user, local, no concurrent-writer concerns that
would justify Postgres. Revisit only if a real multi-process or multi-user
requirement shows up; none is anticipated by this spec.

## 6. Rules engine shape

Every rule is a pure function: `(portfolio_snapshot, rule_config) -> RuleResult`
where `RuleResult` is `{status: pass|breach|warning, computed_value, threshold,
reason}`. Structural rules (position count, sizing, cash floor, core allocation,
cluster caps) operate on the aggregated snapshot alone. Exit rules (ladders,
stops) additionally need per-position entry price and, for the relative stop,
90-day price history for both the asset and BTC. The entry gate (six-point
checklist) is a save-time validation on `position_metadata`, not a scheduled
rule — it belongs in the `/api` layer's write path, not the evaluator loop.

Keeping every rule a pure function over data (no direct exchange calls from
inside the rules engine) is what makes the mock-adapter testing strategy in
spec §9 work — the engine is tested against constructed snapshots, never
against a live or even a mocked adapter directly.

## 7. Open decisions inherited from the spec (§11) — still unresolved

These block parts of Stage 2 onward and should be settled before those stages
start, not discovered mid-build:

1. Runtime: always-on vs. run-on-demand — affects the scheduler design in §2
   above and the notification delivery model.
2. Notification channel: email or Telegram — affects `/notifications`.
3. Cost basis ingestion: manual entry vs. CSV import (CryptoTaxCalculator /
   Koinly) — affects the `position_metadata` write path and whether Stage 4
   needs a CSV parser.
4. Legacy book scope: all ~123 positions for wind-down tracking, or target
   portfolio only — affects how much of the LEGACY dashboard section and the
   dust-conversion flagging (spec §5) gets built in early stages vs. deferred.

## 8. What Stage 1 does not resolve

Per `SWYFTX_API_AUDIT.md` and `SECURITY.md`, several items are marked `UNKNOWN`
and must be confirmed — from a network that can actually reach the relevant
docs, which this sandboxed session could not — before Stage 2 (Swyftx adapter)
or Stage 9 (security review) can be considered complete. This architecture
document assumes those will resolve in the direction the spec anticipates
(numeric asset IDs on Swyftx, scope introspection available on most venues);
if either assumption breaks, the adapter interface in §3 likely still holds,
but the Swyftx adapter's internals and the security fallback in `SECURITY.md`
§2 would need rework.
