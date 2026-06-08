"""F3/F5: passport sign/verify, tamper detection, freshness."""
from datetime import datetime, timedelta, timezone

import pytest

import sdg.paths as paths
from sdg import passport


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "STATE_DIR", tmp_path)
    monkeypatch.setattr(paths, "PASSPORT", tmp_path / "passport.json")
    monkeypatch.setattr(passport, "_SIGN_KEY", tmp_path / "passport.key")


def _make(now):
    return passport.build({"python": {"ok": True}}, {"ram": {"ok": True}},
                          {"ro_RO": {"self_test": "pass"}},
                          ["local", "cloud_pseudonymized"], "0.1.0", now=now)


def test_valid_fresh_passport():
    now = datetime(2026, 6, 8, tzinfo=timezone.utc)
    pp = _make(now)
    ok, reasons = passport.verify(pp, "0.1.0", now=now)
    assert ok, reasons


def test_tamper_detected():
    now = datetime(2026, 6, 8, tzinfo=timezone.utc)
    pp = _make(now)
    pp["paths_enabled"].append("cloud_direct")  # edit without re-signing
    ok, reasons = passport.verify(pp, "0.1.0", now=now)
    assert not ok and any("signature" in r for r in reasons)


def test_expiry():
    now = datetime(2026, 6, 8, tzinfo=timezone.utc)
    pp = _make(now)
    later = now + timedelta(days=31)
    ok, reasons = passport.verify(pp, "0.1.0", now=later)
    assert not ok and any("expired" in r for r in reasons)


def test_version_change_invalidates():
    now = datetime(2026, 6, 8, tzinfo=timezone.utc)
    pp = _make(now)
    ok, reasons = passport.verify(pp, "0.2.0", now=now)
    assert not ok and any("version" in r for r in reasons)
