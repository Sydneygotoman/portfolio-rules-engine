# Portfolio Rules Engine

Read-only multi-exchange portfolio monitoring and rule enforcement tool.
Full spec: [`docs/rules-engine-build-spec.md`](docs/rules-engine-build-spec.md).
Thresholds/rules source of truth: [`docs/investment-rules-v1.md`](docs/investment-rules-v1.md).

## Status: Stage 1 (audit) complete — no application code yet

Per the build spec's own gate ("Stage 1 — Audit only. No application code."),
this stage produced research documents and stops here for review before any
implementation begins:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/SWYFTX_API_AUDIT.md`](docs/SWYFTX_API_AUDIT.md)
- [`docs/CCXT_COVERAGE.md`](docs/CCXT_COVERAGE.md)
- [`docs/SECURITY.md`](docs/SECURITY.md)

**Important caveat:** this audit was produced from a network-sandboxed session
that could not reach `docs.swyftx.com.au`, `docs.ccxt.com`, or most exchange
documentation domains directly (outbound access to those hosts was blocked by
the environment's egress proxy). CCXT method support was confirmed directly
from CCXT's source on GitHub instead, and is solid. Swyftx's actual API
behavior and several venues' key-scope-introspection details are **not**
independently verified — see the `UNKNOWN` items in `SWYFTX_API_AUDIT.md` and
`SECURITY.md` §2 and §8. Those need to be re-checked from an unrestricted
network before Stage 2 (the Swyftx adapter) starts, per the spec's own rule:
"Never guess an API. Mark unknowns and stop."

Do not proceed to Stage 2 without resolving those open items.
