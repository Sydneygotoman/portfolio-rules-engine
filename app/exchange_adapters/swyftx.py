"""Swyftx adapter — the largest holding in this portfolio (~$11.7k per
docs/investment-rules-v1.md), so this is written from the most-corroborated
shape available, but it has **never seen a real 200 response**. Two
independent implementations agree on this shape (the unofficial
`joshturge/goswyftx` Go wrapper, and a second, independently-built
Lovable/Supabase edge function whose live call to `/auth/refresh/` produces
a real 401/403 from Swyftx's actual API — not a 404 or connection error,
which is meaningful corroboration that the base URL and path are right).
See docs/SWYFTX_API_AUDIT.md §0/§1/§4 for the full sourcing. Confirm one
real successful response end-to-end before trusting this with a real key.

Not a CCXT exchange, so this doesn't share ccxt_adapter.py's base class —
Swyftx's own numeric-asset-ID model and native-AUD pricing make it
structurally different anyway (see docs/ARCHITECTURE.md §3).
"""

import base64
import json
import os
import time

import requests

from .base import Balance, ExchangeAdapter

SWYFTX_BASE = "https://api.swyftx.com.au"
AUD_ASSET_ID = 1  # docs/SWYFTX_API_AUDIT.md §4 — live-rates/1/ is rates against AUD itself
ASSET_CACHE_TTL_SECONDS = 12 * 60 * 60
TOKEN_REFRESH_MARGIN_SECONDS = 60


class SwyftxAdapter(ExchangeAdapter):
    venue = "swyftx"

    def __init__(self):
        self._token: str | None = None
        self._token_expires_at: float = 0
        self._last_refresh_response: dict | None = None
        self._asset_map: dict[int, str] | None = None
        self._asset_map_expires_at: float = 0

    def _api_key(self) -> str:
        key = os.environ.get("SWYFTX_API_KEY", "").strip()
        if not key:
            raise RuntimeError("SWYFTX_API_KEY is not set.")
        return key

    def _get_token(self, force: bool = False) -> str:
        now = time.time()
        if not force and self._token and self._token_expires_at > now + TOKEN_REFRESH_MARGIN_SECONDS:
            return self._token

        resp = requests.post(
            f"{SWYFTX_BASE}/auth/refresh/",
            json={"apiKey": self._api_key()},
            timeout=10,
        )
        if resp.status_code in (401, 403):
            raise PermissionError(
                "Swyftx rejected the API key (expired, revoked, or missing required scope)."
            )
        resp.raise_for_status()
        body = resp.json()
        self._last_refresh_response = body

        token = body.get("accessToken")
        if not token:
            raise RuntimeError("Swyftx token refresh returned no accessToken.")

        # Prefer the JWT's own exp claim; fall back to a conservative 1 hour —
        # matches the corroborating Lovable implementation's approach, since
        # the actual token lifetime isn't independently confirmed (audit §1).
        expires_at = now + 3600
        parts = token.split(".")
        if len(parts) == 3:
            try:
                padded = parts[1] + "=" * (-len(parts[1]) % 4)
                payload = json.loads(base64.urlsafe_b64decode(padded))
                if "exp" in payload:
                    expires_at = float(payload["exp"])
            except Exception:
                pass

        self._token = token
        self._token_expires_at = expires_at
        return token

    def _authed_get(self, path: str) -> dict | list:
        token = self._get_token()
        resp = requests.get(f"{SWYFTX_BASE}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        if resp.status_code == 401:
            token = self._get_token(force=True)
            resp = requests.get(f"{SWYFTX_BASE}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        if resp.status_code in (401, 403):
            raise PermissionError(
                "Swyftx rejected the API key (expired, revoked, or missing required scope)."
            )
        resp.raise_for_status()
        return resp.json()

    def _get_asset_map(self) -> dict[int, str]:
        now = time.time()
        if self._asset_map is not None and self._asset_map_expires_at > now:
            return self._asset_map
        assets = self._authed_get("/markets/assets/")
        asset_map = {a["id"]: a.get("code", f"#{a['id']}") for a in assets if "id" in a}
        self._asset_map = asset_map
        self._asset_map_expires_at = now + ASSET_CACHE_TTL_SECONDS
        return asset_map

    def get_balances(self) -> list[Balance]:
        raw = self._authed_get("/user/balance/")
        asset_map = self._get_asset_map()
        balances = []
        for row in raw:
            asset_id = row.get("assetId")
            amount = float(row.get("availableBalance", 0) or 0)
            if not amount or asset_id == AUD_ASSET_ID:
                continue
            code = asset_map.get(asset_id, f"#{asset_id}")
            balances.append(Balance(venue=self.venue, asset=code, quantity=amount))
        return balances

    def get_cash_balance(self) -> float:
        raw = self._authed_get("/user/balance/")
        for row in raw:
            if row.get("assetId") == AUD_ASSET_ID:
                return float(row.get("availableBalance", 0) or 0)
        return 0.0

    def get_prices(self, assets: list[str]) -> dict[str, float]:
        asset_map = self._get_asset_map()
        code_to_id = {code: aid for aid, code in asset_map.items()}
        raw = self._authed_get(f"/live-rates/{AUD_ASSET_ID}/")
        prices = {}
        for asset in assets:
            asset_id = code_to_id.get(asset)
            if asset_id is None:
                continue
            entry = raw.get(str(asset_id))
            if entry and entry.get("midPrice") is not None:
                prices[asset] = float(entry["midPrice"])
        return prices

    def get_key_scopes(self) -> list[str]:
        """No confirmed introspection endpoint exists (audit §2), though the
        `/auth/refresh/` response carries an unexamined `scope` field that
        may turn out to be exactly this — see the audit's top-priority open
        item. Until that's checked against a real response, this requires
        explicit operator attestation, same fail-closed pattern as Gate."""
        if os.environ.get("SWYFTX_ATTESTED_READONLY", "").strip().lower() != "true":
            raise RuntimeError(
                "Swyftx has no confirmed API endpoint to verify this key's own scopes "
                "(see docs/SWYFTX_API_AUDIT.md §2). Set SWYFTX_ATTESTED_READONLY=true "
                "only after confirming in the Swyftx UI that this key was created with "
                "balance/read scopes only, no order-placement or withdrawal scope."
            )
        self._get_token()  # populate _last_refresh_response as a side effect
        scopes = ["general_read_only"]
        if self._last_refresh_response and self._last_refresh_response.get("scope"):
            raw_scope = self._last_refresh_response["scope"]
            reported = raw_scope if isinstance(raw_scope, list) else str(raw_scope).replace(",", " ").split()
            scopes.append("swyftx_reported:" + "+".join(reported))
        return scopes

    def health(self) -> bool:
        try:
            self._get_token()
            return True
        except Exception:
            return False
