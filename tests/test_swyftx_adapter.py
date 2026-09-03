"""Tests the adapter's parsing logic against the shapes documented in
docs/SWYFTX_API_AUDIT.md — mocked HTTP, since this session cannot reach a
real Swyftx endpoint (network egress to exchange APIs is blocked here; see
the audit's §0). These confirm our code handles the confirmed shape
correctly; they do not confirm the shape itself matches production."""

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from app.exchange_adapters.swyftx import SwyftxAdapter


def make_jwt(exp: float) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).rstrip(b"=").decode()
    return f"{header}.{payload}.sig"


@pytest.fixture
def adapter(monkeypatch):
    monkeypatch.setenv("SWYFTX_API_KEY", "test-key")
    return SwyftxAdapter()


def _response(status_code=200, json_body=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    if status_code >= 400 and status_code not in (401, 403):
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    else:
        resp.raise_for_status.return_value = None
    return resp


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("SWYFTX_API_KEY", raising=False)
    a = SwyftxAdapter()
    with pytest.raises(RuntimeError):
        a._get_token()


def test_auth_refresh_rejection_raises_permission_error(adapter):
    with patch("app.exchange_adapters.swyftx.requests.post", return_value=_response(401)):
        with pytest.raises(PermissionError):
            adapter._get_token()


def test_auth_refresh_success_caches_token_from_jwt_exp(adapter):
    token = make_jwt(exp=9999999999)
    with patch("app.exchange_adapters.swyftx.requests.post", return_value=_response(200, {"accessToken": token})):
        result = adapter._get_token()
    assert result == token
    assert adapter._token_expires_at == 9999999999


def test_get_balances_resolves_ticker_and_excludes_aud(adapter):
    token = make_jwt(exp=9999999999)
    with patch("app.exchange_adapters.swyftx.requests.post", return_value=_response(200, {"accessToken": token})):
        with patch(
            "app.exchange_adapters.swyftx.requests.get",
            side_effect=[
                _response(200, [{"assetId": 1, "availableBalance": "150.0"}, {"assetId": 3, "availableBalance": "0.05"}]),
                _response(200, [{"id": 1, "code": "AUD"}, {"id": 3, "code": "BTC"}]),
            ],
        ):
            balances = adapter.get_balances()
    assert len(balances) == 1
    assert balances[0].asset == "BTC"
    assert balances[0].quantity == 0.05


def test_get_cash_balance_reads_asset_id_1(adapter):
    token = make_jwt(exp=9999999999)
    with patch("app.exchange_adapters.swyftx.requests.post", return_value=_response(200, {"accessToken": token})):
        with patch(
            "app.exchange_adapters.swyftx.requests.get",
            return_value=_response(200, [{"assetId": 1, "availableBalance": "250.5"}]),
        ):
            cash = adapter.get_cash_balance()
    assert cash == 250.5


def test_get_prices_reads_mid_price_by_resolved_asset_id(adapter):
    token = make_jwt(exp=9999999999)
    with patch("app.exchange_adapters.swyftx.requests.post", return_value=_response(200, {"accessToken": token})):
        with patch(
            "app.exchange_adapters.swyftx.requests.get",
            side_effect=[
                _response(200, [{"id": 3, "code": "BTC"}]),  # asset map
                _response(200, {"3": {"midPrice": "148000.5"}}),  # live-rates/1/
            ],
        ):
            prices = adapter.get_prices(["BTC"])
    assert prices == {"BTC": 148000.5}


def test_get_key_scopes_fails_closed_without_attestation(adapter, monkeypatch):
    monkeypatch.delenv("SWYFTX_ATTESTED_READONLY", raising=False)
    with pytest.raises(RuntimeError, match="SWYFTX_ATTESTED_READONLY"):
        adapter.get_key_scopes()


def test_get_key_scopes_reports_reported_scope_when_attested(adapter, monkeypatch):
    monkeypatch.setenv("SWYFTX_ATTESTED_READONLY", "true")
    token = make_jwt(exp=9999999999)
    with patch(
        "app.exchange_adapters.swyftx.requests.post",
        return_value=_response(200, {"accessToken": token, "scope": "read balance"}),
    ):
        scopes = adapter.get_key_scopes()
    assert "general_read_only" in scopes
    assert any("swyftx_reported" in s for s in scopes)


def test_get_key_scopes_still_raises_on_real_rejection_even_if_attested(adapter, monkeypatch):
    monkeypatch.setenv("SWYFTX_ATTESTED_READONLY", "true")
    with patch("app.exchange_adapters.swyftx.requests.post", return_value=_response(401)):
        with pytest.raises(PermissionError):
            adapter.get_key_scopes()
