# BUILD SPECIFICATION — Portfolio Rules Engine (v2)

**Read-only multi-exchange monitoring and rule enforcement.**
Companion document: `investment-rules-v1.md` — that file is the source of truth for every threshold below.

---

## 0. What this is

A local application that:

1. Reads balances from five exchanges via **read-only** API keys
2. Joins them with locally-stored position metadata (thesis, entry, ladder, stops)
3. Evaluates the rule set in `investment-rules-v1.md`
4. Surfaces breaches on a dashboard and via notification

It is a **monitoring and discipline tool**. It observes and reports. It never acts.

---

## 1. Absolute boundaries — non-negotiable

The application must **never**:

- Place, modify, or cancel an order
- Withdraw, transfer, or deposit funds
- Hold an API key with trading or withdrawal scope
- Expose any credential to the frontend, browser storage, logs, or Git
- Use leverage, margin, derivatives, or perpetuals in any form
- Auto-execute any decision

**API keys must be created with read-only / view / general permission only.** If a key can place an order, it is the wrong key and must be revoked and reissued. This is verified at startup: the app must attempt to enumerate its own key permissions where the exchange API exposes them, and refuse to start if trading scope is detected.

There is no order module, no execution service, no webhook receiver, and no trading toggle anywhere in this codebase. Do not build one. Do not scaffold one "for later."

---

## 2. Venues

| Venue | Integration | Notes |
|---|---|---|
| **Swyftx** | **Custom adapter** | Not supported by CCXT. Largest holding (~$11.7k). |
| Coinbase | CCXT | |
| KuCoin | CCXT | Requires key + secret + passphrase |
| Gate | CCXT | |
| Crypto.com | CCXT | |

### Swyftx API — verify before implementing

Reported behaviour, **must be confirmed against current official docs at `docs.swyftx.com.au` in Stage 1**:

- Auth: API key acts as a refresh token; POST to obtain a short-lived JWT; use as `Bearer`
- Scopes exist and are attached to the key at creation
- Rate limits apply per endpoint (~300 req/min reported on some)
- A demo/sandbox mode exists, with documented differences from production
- Asset identifiers may be numeric IDs rather than tickers — confirm

**Do not invent endpoints.** Anything unverifiable is marked `UNKNOWN` and implementation stops there pending review.

Reference implementations (e.g. `tswallen/swyftx-python`) may be read for orientation only. Audit for stale assumptions; do not copy.

---

## 3. Data model

The central design fact: **exchanges know balances; they do not know your thesis.**

### Sourced from exchanges (live, refreshed)
- Asset, quantity, venue
- Current price / valuation

### Sourced locally (user-entered, persisted)
- Cost basis and entry date
- Written thesis (2 sentences)
- Named catalyst + date window
- Written invalidation condition
- Ladder levels (3x / 5x / 10x target prices)
- Hard stop price
- Time stop date
- Narrative cluster tag (e.g. `solana`, `ai`, `rwa`)
- Classification: `core` | `satellite` | `legacy`

### Critical: positions aggregate by ASSET, not by venue

AERO is held on both Swyftx and KuCoin. EDU, NAKA, GFI and CSPR are also split. A position is the **sum across all venues**. Weight limits are enforced against the aggregate. A per-venue view is a display option, never the basis for a rule check.

### Cost basis

Exchanges are unreliable here — Swyftx records transferred-in coins at transfer-date market price rather than actual purchase price (RENDER: recorded ~$6.29, actually ~$0.40). KuCoin and Gate track none at all.

Cost basis is therefore **user-entered or imported from the tax tracker (CryptoTaxCalculator / Koinly CSV export)**. Never trust the exchange figure. Flag any position where the entered basis differs materially from the venue's reported figure.

### Tables

`positions`, `position_metadata`, `venues`, `balances_snapshot`, `prices`, `rule_evaluations`, `breaches`, `journal_entries`, `system_events`

---

## 4. Rules engine

Evaluates on a schedule and on demand. Every rule returns: `pass` | `breach` | `warning`, with the computed value, the threshold, and a human-readable reason.

### Structural rules

| Rule | Threshold | Check |
|---|---|---|
| Position count | ≤ 10 | Count of non-legacy positions |
| Min position size | ≥ 5% of total | Flag anything below |
| Max position size | ≤ 20% of total | Breach → trim to 20% |
| Cash floor | ≥ 20% | Aggregate cash across venues |
| Core allocation | BTC+ETH ≥ 50% | Report current % and dollar gap |
| Narrative cluster | ≤ 25% per tag | Sum by cluster tag |

### Exit rules

| Rule | Trigger |
|---|---|
| Ladder — 3x | Current price ≥ 3× entry → sell 33% |
| Ladder — 5x | ≥ 5× entry → sell 25% |
| Ladder — 10x | ≥ 10× entry → sell 25% |
| Hard stop | ≤ −35% from entry |
| Time stop | 12 months from entry, no catalyst progress |
| Relative stop | Underperforming BTC by ≥30% over trailing 90 days |
| Thesis invalidation | Manual flag |

**The relative stop is the highest-value rule in the system.** It requires 90-day price history for the asset and for BTC. Build the price history store first — everything else depends on it.

### Entry gate

New positions cannot be saved without all six checklist fields populated (value accrual mechanism, named catalyst + date, written invalidation, unlock schedule %, liquidity note, fresh-cash-test answer). Empty fields block the save. This is the point of the tool.

Alts additionally require: outperforming BTC over trailing 90 days at time of entry. Warn on breach; do not hard-block (BTC/ETH are exempt).

---

## 5. Dashboard

Local web UI. Dark. Sections:

**OVERVIEW** — total value across venues, allocation vs targets (core / satellite / cash / legacy), open breach count, next scheduled actions

**BREACHES** — the primary screen. Every rule currently failing, sorted by severity, each with the computed value, threshold, and required action

**POSITIONS** — aggregated by asset, showing venue split, weight, thesis, catalyst, days to time stop, distance to next ladder level, distance to hard stop, 90-day performance vs BTC

**ADD POSITION** — the six-point checklist form. Cannot save incomplete.

**CONTRIBUTIONS** — $500/month schedule, deployment split, core gap tracker, next contribution date

**LEGACY** — the wind-down book, disposal staging, positions below exchange minimum order size flagged as dust-convert-only

**JOURNAL** — weekly entries, position notes, rule amendment log

**SYSTEM** — per-venue connection status, last successful sync, last error, key scope verification result

---

## 6. Notifications

Configurable channel (email or Telegram). Triggers:

- Any hard stop breached
- Any ladder level reached
- Time stop within 14 days
- Relative stop triggered
- Allocation breach (weight, cash floor, cluster)
- Venue sync failure > 24h
- Weekly review reminder

Never include credentials or full balances in notification bodies.

---

## 7. Security

- Secrets in environment variables only. `.env.example` committed; `.env` in `.gitignore`
- No credentials in source, logs, error messages, frontend, or browser storage
- Read-only scopes verified at startup; refuse to start on trading scope
- IP allowlisting on exchange keys where supported
- Local-only binding by default (`127.0.0.1`). If exposed, HTTPS + auth required
- Encrypt keys at rest if persisted beyond env vars
- Rate limit outbound API calls per venue's documented limits

---

## 8. Architecture

```
/exchange-adapters   # ExchangeAdapter interface; ccxt wrapper + custom swyftx
/price-service       # price history, BTC-relative performance
/rules-engine        # rule definitions and evaluation
/api                 # FastAPI backend
/frontend            # dashboard
/database            # PostgreSQL (or SQLite for single-user local)
/notifications
/tests
/docs
```

**Adapter interface** — all venue code sits behind it, no exchange calls elsewhere:

```
get_balances()      -> list[Balance]
get_prices(assets)  -> dict[asset, price]
get_key_scopes()    -> list[scope]   # for startup verification
health()            -> status
```

Four methods. No order methods. Do not add any.

SQLite is acceptable and probably preferable for a single-user local app. PostgreSQL only if a real reason emerges.

---

## 9. Testing

- Mock adapter for every venue — never hit live APIs in tests
- Every rule tested at boundary, above, and below threshold
- Multi-venue aggregation (the AERO/EDU/NAKA/GFI/CSPR duplicate case)
- Cost basis mismatch detection
- Startup refusal when a trading-scoped key is present
- Venue outage / partial data handling: **stale data must be visibly stale, never silently shown as current**

---

## 10. Stages — build in order, stop at each gate

**Stage 1 — Audit only. No application code.**
Produce:
- `ARCHITECTURE.md`
- `SWYFTX_API_AUDIT.md` — verified auth, endpoints, scopes, rate limits, asset IDs, and an explicit `UNKNOWN` list
- `CCXT_COVERAGE.md` — confirmed method support for Coinbase / KuCoin / Gate / Crypto.com
- `SECURITY.md` — key scopes required per venue, threat model, no-execution guarantee

Stop. Review before proceeding.

**Stage 2** — Swyftx read-only adapter + tests against mock
**Stage 3** — CCXT adapters for remaining four venues
**Stage 4** — Position store, metadata model, multi-venue aggregation
**Stage 5** — Price history service and BTC-relative performance (blocks the relative stop)
**Stage 6** — Rules engine
**Stage 7** — Dashboard
**Stage 8** — Notifications
**Stage 9** — Security review
**Stage 10** — Local deploy, scheduled sync

---

## 11. Open decisions — resolve before Stage 1

1. **Runtime** — always-on machine, or run-on-demand? Affects scheduling and notification design.
2. **Notification channel** — email or Telegram.
3. **Cost basis ingestion** — manual entry, or CSV import from CryptoTaxCalculator / Koinly.
4. **Legacy book** — load all ~123 positions for wind-down tracking, or target portfolio only?

---

## 12. Critical rules

- Never guess an API. Mark unknowns and stop.
- Never assume a GitHub reference implementation is current.
- Never request or use a key with trading or withdrawal scope.
- Never build an execution path, even as a stub.
- Never display stale data as current.
- Never trust exchange-reported cost basis.

---

## 13. First task

**Do not write application code.**

Inspect: current Swyftx official API docs; CCXT's current support for Coinbase, KuCoin, Gate and Crypto.com; the read-only scope model for each of the five venues.

Produce the four Stage 1 documents. Identify everything unverifiable. Then stop and wait for approval.
