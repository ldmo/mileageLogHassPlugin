"""Unit tests for Traxmiles parsing helpers."""

from __future__ import annotations

from pathlib import Path

from custom_components.traxmiles.client import (
    extract_csrf_token,
    extract_edit_lock_url,
    parse_home_snapshot,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_extract_csrf_token_prefers_meta() -> None:
    html = _read_fixture("login.html")
    assert extract_csrf_token(html) == "login_csrf_token_123"


def test_parse_home_snapshot_open() -> None:
    html = _read_fixture("home_open.html")
    snapshot = parse_home_snapshot(html)

    assert snapshot.csrf_token == "home_open_csrf_456"
    assert snapshot.record_id == "2625396"
    assert snapshot.open_record_month == "April 2026"
    assert snapshot.is_locked is False
    assert snapshot.business_miles_this_month == 123.4
    assert snapshot.total_business_miles_tax_year == 456.7
    assert snapshot.opening_odometer == 54317.0
    assert snapshot.vehicle_registration == "MV73PYF"


def test_parse_home_snapshot_locked() -> None:
    html = _read_fixture("home_locked.html")
    snapshot = parse_home_snapshot(html)

    assert snapshot.csrf_token == "home_locked_csrf_789"
    assert snapshot.record_id == "9999999"
    assert snapshot.open_record_month == "April 2026"
    assert snapshot.is_locked is True
    assert snapshot.business_miles_this_month == 200.0
    assert snapshot.total_business_miles_tax_year == 1000.0
    assert snapshot.opening_odometer == 12345.0
    assert snapshot.vehicle_registration == "AB12CDE"


def test_extract_edit_lock_url_when_missing() -> None:
    assert extract_edit_lock_url("<html><body>No link</body></html>") is None
