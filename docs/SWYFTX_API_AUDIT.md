# Swyftx API Audit

Status: **INCOMPLETE — verification blocked by this environment's network egress policy.**
Do not proceed to Stage 2 (Swyftx adapter) until every item marked `UNKNOWN` below
has been confirmed against `docs.swyftx.com.au` from an environment that can reach it.

## 0. What could and could not be checked

This audit was produced from a sandboxed session whose outbound network access is
restricted by an egress proxy. The following hosts — which are exactly the ones that
matter for this audit — returned `EGRESS_BLOCKED` on every attempt:

- `docs.swyftx.com.au` (official API reference — the actual source of truth)
- `api.swyftx.com.au` and `api.demo.swyftx.com.au`
- `support.swyftx.com`, `help.swyftx.com.au`
- `swyftx.docs.apiary.io`, `jsapi.apiary.io` (older Apiary-hosted docs)
- `cointracking.info` (third-party integration guide)

What *did* work: general web search (search-engine result summaries, not the raw
pages) and `raw.githubusercontent.com` (so unofficial GitHub reference
implementations could be read, per the build spec's allowance to read them "for
orientation only").

**Consequence:** nothing below sourced from the official docs is independently
verified. Anything sourced only from search-result summaries or from third-party
wrapper libraries is marked accordingly and must be treated as a hypothesis, not
a fact, until someone with unrestricted network access re-runs this audit against
`docs.swyftx.com.au` directly.

## 1. Authentication

| Claim | Status | Source |
|---|---|---|
| API key is a long-lived credential; it is exchanged for a short-lived JWT via a refresh endpoint | Reported consistently across independent sources | Search summaries (Swyftx support/help articles), goswyftx source |
| Refresh endpoint path is `auth/refresh/`, `POST`, body `{"apiKey": "..."}`, response contains `accessToken` | **UNKNOWN — unverified**, sourced only from an unofficial Go wrapper (`joshturge/goswyftx`), not from official docs | `raw.githubusercontent.com/joshturge/goswyftx/master/authentication.go` |
| JWT is sent as `Authorization: Bearer <token>` on subsequent requests | Reported consistently | Search summaries |
| Base URL production: `https://api.swyftx.com.au` | Reported consistently, matches multiple independent sources including the Go wrapper | Search summaries + goswyftx `client.go` |
| Base URL demo: `https://api.demo.swyftx.com.au` | Reported consistently | Search summaries; note one older wrapper (goswyftx) instead points its demo constant at a now-probably-stale Apiary mock URL — **do not use that value**, it postdates the real demo host by several years |
| JWT lifetime / refresh frequency required | **UNKNOWN** | No source found |

## 2. Scopes / permissions on API keys

| Claim | Status |
|---|---|
| Keys are created with a checklist of named permission scopes at creation time (e.g. "Balance", "Order History", "Read", "Tax Report" were named in secondary sources) | Reported, but the **complete enumerated list of scope names is UNKNOWN** — search results only surfaced a handful of named examples, not an exhaustive list, and could not reach the actual key-creation UI or its docs page |
| A scope exists that is trade/order-placement-capable, separate from balance/read scopes | Plausible given the checklist model, but **UNKNOWN** whether it is named e.g. "Order Placement" or "Trade" — needs confirmation |
| Whether the API exposes a **programmatic** endpoint to enumerate a given key's own granted scopes (needed for the build spec's mandatory startup scope-verification check) | **UNKNOWN — this is the single most important open item.** If no such endpoint exists, the spec's requirement to "refuse to start if trading scope is detected" cannot be implemented by introspection and would have to fall back to a manually-configured allowlist of scope names checked against what the operator declares the key was created with — a materially weaker guarantee. Must be resolved before Stage 1 sign-off. |

## 3. Rate limits

| Claim | Status |
|---|---|
| ~300 requests/minute reported for at least `getLatestBar` / `getBars`-style endpoints | One source only (Apiary-hosted reference, found via search snippet, page itself unreachable) |
| Whether this limit is global, per-endpoint, or per-key | **UNKNOWN** |
| Rate limits for the balance and live-rates endpoints specifically | **UNKNOWN** |

Treat 300 req/min as an unconfirmed upper bound to design against defensively (i.e.
build the adapter's rate limiter to be far more conservative — e.g. batch balance +
price polling into one sync per minute), not as a value to rely on.

## 4. Asset identifiers

| Claim | Status |
|---|---|
| Balance endpoint (`user/balance/` per one unofficial wrapper) returns holdings keyed by a **numeric asset ID**, not a ticker | Sourced only from an unofficial Go wrapper — **UNKNOWN**, unverified against official docs |
| A separate market-info endpoint (`markets/info/basic/{code}` per the same wrapper) accepts a **ticker string** | Same source, same caveat |
| Whether there is an official, current asset-ID ↔ ticker mapping endpoint (e.g. an `assets` list) that should be cached at startup | **UNKNOWN** |

If the numeric-ID claim holds, the Swyftx adapter needs an asset-ID↔ticker resolution
table refreshed from whatever the live "list assets" endpoint turns out to be, since
every other venue in this system (CCXT-based) and the local position store key
everything by ticker/asset symbol per `rules-engine-build-spec.md` §3.

## 5. Demo/sandbox mode

| Claim | Status |
|---|---|
| A demo environment exists at `api.demo.swyftx.com.au` with a documented but unspecified subset of endpoint coverage | Reported consistently in search summaries; exact list of which endpoints differ is **UNKNOWN** |

## 6. Endpoints needed by this build (all UNKNOWN pending confirmation)

The following are **guesses drawn from an unofficial, unmaintained wrapper** and are
listed only so Stage 2 has a concrete checklist to verify or discard — **not** to be
implemented as-is:

- Balances: `GET user/balance/` *(unverified)*
- Live price: `GET live-rates/{numeric_asset_id}` *(unverified)*
- Asset metadata by ticker: `GET markets/info/basic/{ticker}` *(unverified)*
- Refresh token → JWT: `POST auth/refresh/` *(unverified)*
- Key scope introspection endpoint: **not found in any source** — see §2

## 7. What Stage 1 sign-off requires before Stage 2 can start

1. Direct access to `docs.swyftx.com.au` from a network that isn't proxy-restricted, to confirm or replace every row above.
2. An explicit answer on whether key-scope introspection is possible via the API (§2) — this gates whether the spec's mandatory startup trading-scope refusal can be built as specified.
3. Confirmation of the numeric-asset-ID model and the correct endpoint to resolve IDs to tickers (§4).
4. A current rate-limit figure per endpoint actually used (§3).

Per the build spec ("Do not invent endpoints... anything unverifiable is marked
UNKNOWN and implementation stops there pending review"), **Stage 2 should not begin
until this document has no unresolved `UNKNOWN` in §2 and §4** — those two are load-bearing
for the security guarantee and the data model, respectively.
