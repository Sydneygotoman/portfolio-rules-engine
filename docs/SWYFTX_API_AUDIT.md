# Swyftx API Audit

Status: **Mostly confirmed as of 2026-09-03**, via a second, independent implementation
(a Lovable/Supabase edge-function project, `src/lib/swyftx.server.ts` in project
`278209cb-3b19-4f98-a282-ef060c7743f4`) built from an environment that could actually
reach `docs.swyftx.com.au` — this sandboxed session still cannot (see §0). That
implementation's own header comment claims it was "Verified against
https://docs.swyftx.com.au (Apiary)", and — more convincingly than a claim alone —
it produces a **live 401/403 rejection from Swyftx's real API** ("Swyftx rejected
the API key (expired, revoked, or missing the required read scopes)"), which means
the base URL, the `/auth/refresh/` path, and the request shape are real enough to
reach Swyftx's auth layer and get a credential-specific rejection back, not a 404
or a connection failure. That's strong behavioral corroboration of the structure
below, on top of it independently matching the unofficial Go wrapper's shape
(§1/§4) that was the only prior source. It is **not** the same as a confirmed
end-to-end success — nobody has yet seen a real 200 response with real balances
back through this shape. Treat §1 and part of §4 as confirmed; §2 (scopes) and §3
(rate limits) are still open.

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
| API key is a long-lived credential; it is exchanged for a short-lived JWT via a refresh endpoint | **Confirmed** (independently implemented, produces a real credential-specific rejection rather than 404/network error) | `swyftx.server.ts`, corroborated by search summaries + goswyftx |
| Refresh endpoint: `POST /auth/refresh/`, body `{"apiKey": "..."}`, response `{accessToken, scope, ...}` | **Confirmed** — matches the unofficial Go wrapper exactly, and is the exact call that produces the live 401/403 | `swyftx.server.ts` |
| JWT is sent as `Authorization: Bearer <token>` on subsequent requests | **Confirmed** | `swyftx.server.ts` |
| Base URL production: `https://api.swyftx.com.au` | **Confirmed** | `swyftx.server.ts`, goswyftx |
| Base URL demo: `https://api.demo.swyftx.com.au` | Reported consistently in search summaries, not exercised by either implementation | — |
| JWT lifetime / refresh frequency | **UNKNOWN precisely** — `swyftx.server.ts` decodes the JWT's own `exp` claim and falls back to a conservative 1-hour assumption when absent; treat that as the safe default rather than a confirmed figure | `swyftx.server.ts` |
| Response includes a `scope` field alongside `accessToken` | **New finding, unconfirmed meaning** — `swyftx.server.ts`'s type hints at a `scope` field on the refresh response but doesn't parse or use it. Worth checking directly: this could be exactly the per-key granted-scope signal §2 needs, making it available for free on every token refresh rather than needing a separate introspection call | `swyftx.server.ts` |

## 2. Scopes / permissions on API keys

| Claim | Status |
|---|---|
| Keys are created with a checklist of named permission scopes at creation time (e.g. "Balance", "Order History", "Read", "Tax Report" were named in secondary sources) | Reported, but the **complete enumerated list of scope names is still UNKNOWN** |
| A scope exists that is trade/order-placement-capable, separate from balance/read scopes | Plausible given the checklist model, but **UNKNOWN** whether it is named e.g. "Order Placement" or "Trade" |
| Whether the API exposes a way to check a key's own granted scopes at runtime | **Promising new lead, not yet confirmed**: `swyftx.server.ts`'s refresh-response type includes a `scope` field alongside `accessToken` — if `POST /auth/refresh/` really does return the key's granted scope(s) on every call, that *is* the startup scope-verification mechanism the build spec requires, for free, no separate endpoint needed. Nobody has actually inspected the value of that field yet (the Lovable implementation's code never reads it). **This is the single highest-priority thing to check next**: get one successful (200) `/auth/refresh/` response and log the full raw JSON body, not just `accessToken`. |

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
| Balance endpoint returns holdings keyed by a **numeric asset ID**, not a ticker: `GET /user/balance/` -> `[{assetId: number, availableBalance: string}]` | **Confirmed**, matches the unofficial Go wrapper exactly and is part of the shape producing the live rejection |
| Asset ID -> ticker mapping endpoint: `GET /markets/assets/` -> `[{id, code, name}]` | **Confirmed** by the same independent implementation — this is the missing piece the earlier audit flagged as unconfirmed |
| Live AUD prices: `GET /live-rates/1/` -> `{"<assetId>": {midPrice, askPrice, bidPrice, dailyPriceChange}}` | **Confirmed**, and clarifies something the earlier audit didn't know: **asset ID `1` is AUD itself** — `live-rates/1/` reads as "rates against base currency 1 (AUD)", and the implementation hardcodes `priceAud = 1` when `assetId === 1` rather than looking it up. This resolves the FX problem for Swyftx specifically: prices are natively AUD, no conversion needed, unlike the CCXT venues or the Crypto.com-backed Artifact (both USD-first) |

The Swyftx adapter needs an asset-ID↔ticker resolution table from `/markets/assets/`,
refreshed periodically (cache for a reasonable window, e.g. `swyftx.server.ts` uses 12h),
since the local position store and every other venue in this system key by ticker
symbol per `rules-engine-build-spec.md` §3.

## 5. Demo/sandbox mode

| Claim | Status |
|---|---|
| A demo environment exists at `api.demo.swyftx.com.au` with a documented but unspecified subset of endpoint coverage | Reported consistently in search summaries; exact list of which endpoints differ is **UNKNOWN** |

## 6. Endpoints needed by this build

Confirmed by two independent implementations (the unofficial `goswyftx` wrapper, and
the Lovable/Supabase edge function that gets a live rejection from these exact calls):

- Balances: `GET /user/balance/` *(confirmed shape; response not yet seen with a working key)*
- Asset ID -> ticker: `GET /markets/assets/` *(confirmed shape)*
- Live AUD rates: `GET /live-rates/1/` *(confirmed shape; asset id 1 = AUD)*
- Refresh token -> JWT: `POST /auth/refresh/` *(confirmed — this is the exact call producing the live 401/403)*
- Key scope introspection: **still no dedicated endpoint found**, but see §2's `scope`-field lead on the refresh response — check that before assuming one doesn't exist

## 7. Remaining open items

§4 (asset identifiers) is now resolved. Still open:

1. **§2 — read the `scope` field on a real `/auth/refresh/` response.** This is the
   one thing standing between "no known way to verify a key is read-only" and
   "verified on every token refresh, for free." Get one real (non-401) response and
   log the full body.
2. **§3 — current rate limits** for `/user/balance/`, `/markets/assets/`, and
   `/live-rates/1/` specifically. Still unconfirmed; design the adapter's polling
   conservatively (e.g. one combined sync per minute) regardless.
3. **Get past the current key rejection** in the Lovable project (§0) to see one real
   200 response end-to-end — everything above is corroborated by a 401/403's shape,
   not by a successful response. The rejection is very likely the stored
   `SWYFTX_API_KEY` itself (expired, regenerated since being pasted in, or created
   without balance-read scope) rather than a code bug, but that's worth confirming
   before assuming the code is exactly right.

Given the strength of the corroboration (two independent implementations agreeing,
one producing a live credential-specific rejection), the adapter code in
`app/exchange_adapters/swyftx.py` proceeds on this confirmed shape — but it is
**not yet exercised against a real 200 response**, so treat it as implemented-but-
unverified-end-to-end, the same caution as the CCXT adapters.
