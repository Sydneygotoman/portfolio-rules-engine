# Security — Portfolio Rules Engine

This system holds read access to five real exchange accounts and, indirectly,
describes real financial positions. This document is the threat model and the
no-execution guarantee referenced by `rules-engine-build-spec.md` §1 and §7.

## 1. No-execution guarantee

This application is read-only by construction, not just by convention:

- The `ExchangeAdapter` interface (spec §8) exposes exactly four methods —
  `get_balances`, `get_prices`, `get_key_scopes`, `health` — and no others. There
  is no `place_order`, `cancel_order`, `withdraw`, or `transfer` method on the
  interface, so no adapter implementation can expose one to the rest of the system
  without first changing the interface itself, which is a visible, reviewable diff.
- No order module, execution service, webhook receiver, or trading toggle exists
  anywhere in this codebase, and none is to be added — including as a stub,
  disabled route, or "for later" scaffold. Code review should treat any PR that
  adds an order-shaped method anywhere in `/exchange-adapters` as an automatic
  reject regardless of stated intent.
- CCXT exposes order methods (`createOrder`, `cancelOrder`, etc.) on every
  exchange class used here. The CCXT wrapper adapters must not call them — this
  has to be enforced by code review and by the adapter interface boundary above,
  since CCXT itself will not stop the call. Consider a lint rule or an
  import-boundary check that fails CI if `create_order`/`cancel_order`/etc. appear
  anywhere outside of a (nonexistent) execution module.

## 2. Startup key-scope verification

The spec requires the app to enumerate its own key permissions at startup and
refuse to start if trading scope is detected. Feasibility per venue:

| Venue | Programmatic scope introspection | Status |
|---|---|---|
| Coinbase (Advanced Trade) | `GET /api/v3/brokerage/key_permissions` returns `can_view`, `can_trade`, `can_transfer`, `can_receive` | Confirmed via search of official CDP docs summary — refuse startup if `can_trade` or `can_transfer` is `true` |
| KuCoin | Permission model (`General` read-only vs `Trade` vs `Transfer`) is set at key creation and is documented, but **no confirmed introspection endpoint** was found in this audit to read a key's own granted permission list back at runtime | **UNKNOWN — needs Stage 2 confirmation.** If no introspection endpoint exists, fall back to: an operator-declared expected-scope config value, checked by attempting a harmless read call and treating any trade-shaped call as forbidden at the code level (see §1) rather than detected at boot |
| Gate | Key permissions (Spot/Margin Trade, Wallet Read-Only, etc.) are set at creation; introspection endpoint **not confirmed** in this audit | Same fallback as KuCoin, pending Stage 3 confirmation |
| Crypto.com | Keys default to read-only ("Can Read") with trading as an opt-in add; introspection endpoint **not confirmed** in this audit | Same fallback, pending Stage 3 confirmation |
| Swyftx | **Unknown whether any introspection endpoint exists at all** — see `SWYFTX_API_AUDIT.md` §2, flagged there as the single highest-priority open item | Blocks Stage 2 sign-off |

Where introspection is unavailable, the startup check degrades from "cryptographic
proof the key cannot trade" to "the app never calls a trade-shaped method, enforced
by the interface boundary in §1, plus an operator attestation of the scopes chosen
at key creation." That gap must be stated explicitly in `SYSTEM` screen status
(spec §5) per venue — never presented to the user as equivalent to a verified check.

## 3. Required key scope per venue (what to actually select when creating keys)

| Venue | Correct scope to grant | Never grant |
|---|---|---|
| Swyftx | Balance / read-only scopes only (exact scope names **unverified**, see audit) | Any scope implying order placement or withdrawal |
| Coinbase | `view` only | `trade`, `transfer` |
| KuCoin | `General` (read-only) only | `Trade`, `Transfer` |
| Gate | Wallet: Read-Only; Spot/Margin Trade: **disabled**; Withdraw: **never enabled** | Trade or withdraw permission of any kind |
| Crypto.com | Default "Can Read" only; do not opt in to trading | Trading-enabled keys |

If a key can place an order or move funds, it is the wrong key — revoke and
reissue with a narrower scope before pointing this app at it.

## 4. Credential handling

- All keys/secrets/passphrases live in environment variables only, loaded via
  `.env` locally. `.env.example` (with placeholder values, no real secrets) is
  committed; `.env` itself is git-ignored.
- No credential is ever logged, included in an error message or stack trace, sent
  to the frontend, or written to browser storage. Log statements and exception
  handlers in `/exchange-adapters` and `/api` need review specifically for
  accidental credential interpolation (e.g. an unhandled exception whose message
  includes a signed request URL with the API key as a query param).
- If keys are ever persisted outside process env vars (e.g. a config store),
  encrypt at rest.
- IP allowlisting enabled on every exchange key where the venue supports it,
  scoped to wherever this app actually runs.
- Local-only binding (`127.0.0.1`) by default; HTTPS + auth required if ever
  exposed beyond localhost.

## 5. Notifications

Notification bodies (email/Telegram) must never include credentials or full
balance figures — spec §6. Breach notifications should carry the rule name,
the computed value, and the threshold, not the full portfolio snapshot.

## 6. Rate limiting and outage handling

- Outbound calls to each venue are rate-limited per that venue's documented
  limits (Swyftx's are unconfirmed — see audit; CCXT-default limits for the other
  four should be treated as a floor, not a ceiling, until cross-checked against
  each venue's current published limits).
- On partial or stale data (a venue sync failure), the dashboard must visibly mark
  that venue's data as stale — never silently show a last-known balance as current.
  This is both a correctness requirement (spec §9) and a security-adjacent one:
  a stale-but-unlabeled breach state could mask a real one.

## 7. Threat model summary

| Threat | Mitigation |
|---|---|
| Leaked read-only API key | Read-only scope means leakage exposes balances/positions, not funds — still a privacy concern, hence env-var-only storage, no logging, `.gitignore`d `.env` |
| Leaked key with accidental trade/withdraw scope | Startup scope check (§2) refuses to run; venue-side key scope selection (§3) is the primary control, the app-level check is defense in depth |
| Compromised host running the app | Local-only binding by default; no exposed execution surface even if the host itself is compromised, since there is nothing on this system capable of moving funds |
| Malicious or buggy dependency (CCXT) calling an order method unexpectedly | Interface boundary (§1) — the app's own code never calls order methods, so a compromised dependency would need to be invoked through a code path that doesn't exist |
| Stale data misread as current, leading to a missed real breach | Explicit staleness flagging (§6), tested per spec §9 |

## 8. Open items before Stage 1 sign-off

1. Confirm or refute key-scope introspection availability for KuCoin, Gate,
   Crypto.com, and Swyftx (§2) — currently only Coinbase is confirmed.
2. Confirm exact Swyftx read-only scope names (blocked by network access in this
   audit — see `SWYFTX_API_AUDIT.md`).
3. Decide and document the fallback behavior (operator attestation + interface
   boundary vs. hard refusal to run) for any venue where introspection turns out
   to be unavailable.
