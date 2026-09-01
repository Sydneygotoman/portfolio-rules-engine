# CCXT Coverage — Coinbase, KuCoin, Gate, Crypto.com

Status: **Confirmed against CCXT source** (`raw.githubusercontent.com/ccxt/ccxt`,
`master` branch, checked 2026-09-01). This is read-only market/account data —
nothing here touches order methods, and none should be wired up.

Caveat: checked against the `master` branch tip, which is a moving target. Before
Stage 3, pin an exact CCXT release version in the project's dependency file and
re-confirm this table against that pinned version's source — `master` can drift.

## Methods needed by this build

Only four capabilities matter for a read-only monitoring tool: balances, current
price, historical price (for the 90-day BTC-relative performance calc), and market
metadata. Order-related capability columns are intentionally omitted — this system
must never call them.

| Exchange (ccxt id) | `fetchBalance` | `fetchTicker` | `fetchTickers` | `fetchOHLCV` | `fetchMarkets` |
|---|---|---|---|---|---|
| `coinbase` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `kucoin` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `gate` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `cryptocom` | ✅ | ✅ | ✅ | ✅ | ✅ |

All four unified methods this system needs are supported natively (not emulated)
on all four venues. `fetchOHLCV` support means the 90-day price-history service
(spec §4, "build the price history store first") can be built directly on CCXT
for these four venues without a custom candle-fetching layer — only Swyftx needs
one, since it isn't a CCXT exchange.

## Required credentials per exchange

| Exchange | `apiKey` | `secret` | `password` (passphrase) | Notes |
|---|---|---|---|---|
| `coinbase` | required | required | — | `requiredCredentials` sets only apiKey + secret |
| `kucoin` | required | required | **required** | Matches the build spec's note that KuCoin needs key + secret + passphrase |
| `gate` | required | required | — | |
| `cryptocom` | required | required | — | |

## Exchange-specific notes relevant to a read-only adapter

- **Coinbase**: CCXT's `coinbase` id wraps both the v2 and v3 (Advanced Trade) APIs
  under configurable options; `fetchBalance` defaults to the v2 accounts endpoint.
  Since the venue's own read-only key scope is called `view` (see `SECURITY.md`),
  confirm during Stage 3 which API version the read-only-scoped key can actually
  reach — a v2-scoped key may not be authorized against v3-only endpoints, or vice
  versa. This needs a live test against a real read-only key, not just a source read.
- **KuCoin**: passphrase is a required credential at the CCXT layer regardless of
  the account's own permission level — the adapter's config/env schema must include
  it even though it isn't a "permission" per se, just part of the signing scheme.
- **Gate**: CCXT id is `gate` (the older `gateio` id is now an alias) — use `gate`
  in new code so version pinning doesn't silently pick up deprecated aliasing
  behavior.
- **Crypto.com**: CCXT id is `cryptocom` (not `crypto` or `cryptodotcom`).

## What this document does not cover

- Exact rate limits CCXT applies per exchange (each exchange class sets its own
  `rateLimit` in milliseconds; pull the actual figures for these four from the
  pinned version once selected, and cross-check them against each venue's current
  published API rate limits rather than trusting CCXT's default alone).
- Whether each venue's own key-creation UI can scope a key to *only* the methods
  above (that's a venue permission-model question, answered in `SECURITY.md`, not
  a CCXT capability question).
