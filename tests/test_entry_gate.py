from datetime import date

from app.rules_engine.entry_gate import check_alt_outperformance, missing_checklist_fields

COMPLETE = {
    "value_accrual": "fee burn",
    "catalyst_name": "mainnet",
    "catalyst_date": "2026-01-01",
    "invalidation": "usage declines",
    "unlock_schedule_pct": 5.0,
    "liquidity_note": "exitable same day",
    "fresh_cash_test": True,
}


def test_complete_checklist_has_no_missing_fields():
    assert missing_checklist_fields(COMPLETE) == []


def test_missing_field_is_detected():
    data = dict(COMPLETE)
    data["invalidation"] = ""
    assert missing_checklist_fields(data) == ["invalidation"]


def test_all_fields_missing():
    assert set(missing_checklist_fields({})) == set(COMPLETE.keys())


def test_falsy_but_valid_values_are_not_missing():
    data = dict(COMPLETE)
    data["fresh_cash_test"] = False  # a valid (if damning) answer, not "missing"
    data["unlock_schedule_pct"] = 0
    assert missing_checklist_fields(data) == []


def test_alt_outperformance_warns_on_underperformance():
    history = {
        "ALT": [(date(2025, 1, 1), 1.0), (date(2025, 4, 1), 0.90)],
        "BTC": [(date(2025, 1, 1), 1.0), (date(2025, 4, 1), 1.20)],
    }
    result = check_alt_outperformance("ALT", history)
    assert result.status == "warning"


def test_alt_outperformance_passes_on_outperformance():
    history = {
        "ALT": [(date(2025, 1, 1), 1.0), (date(2025, 4, 1), 1.50)],
        "BTC": [(date(2025, 1, 1), 1.0), (date(2025, 4, 1), 1.20)],
    }
    result = check_alt_outperformance("ALT", history)
    assert result.status == "pass"


def test_btc_and_eth_exempt_from_outperformance_check():
    assert check_alt_outperformance("BTC", {"BTC": []}) is None
    assert check_alt_outperformance("ETH", {"ETH": []}) is None
