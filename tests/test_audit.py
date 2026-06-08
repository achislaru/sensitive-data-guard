"""F1/F5: audit logging guard + retention."""
import os
from datetime import datetime, timedelta, timezone

import pytest

import sdg.paths as paths
from sdg import audit


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "STATE_DIR", tmp_path)
    monkeypatch.setattr(paths, "AUDIT_DIR", tmp_path / "audit")
    monkeypatch.setattr(paths, "CONV_DIR", tmp_path / "conversations")
    paths.AUDIT_DIR.mkdir(parents=True)
    paths.CONV_DIR.mkdir(parents=True)


def test_log_types_only_guard():
    now = datetime(2026, 6, 8, tzinfo=timezone.utc)
    audit.log_interaction("andrei", "hr", "local", {"RO_CNP": 20}, now=now)
    # passing a value instead of a count must be refused
    with pytest.raises(AssertionError):
        audit.log_interaction("x", "y", "local", {"RO_CNP": "2850512123456"}, now=now)


def test_invalid_path_and_channel():
    now = datetime(2026, 6, 8, tzinfo=timezone.utc)
    with pytest.raises(AssertionError):
        audit.log_interaction("x", "y", "cloud_raw", {}, now=now)
    with pytest.raises(AssertionError):
        audit.log_interaction("x", "y", "local", {}, source_channel="email", now=now)


def test_retention_deletes_and_anonymizes():
    now = datetime(2026, 6, 8, tzinfo=timezone.utc)
    audit.log_interaction("andrei", "hr", "local", {"PERSON": 1}, now=now)
    audit.log_interaction("maria", "hr", "local", {"PERSON": 1},
                          now=now - timedelta(days=395))
    old = paths.CONV_DIR / "old.json"
    old.write_text("{}")
    t = (now - timedelta(days=91)).timestamp()
    os.utime(old, (t, t))

    report = audit.apply_retention(now=now)
    assert report["conversations_deleted"] == 1
    assert report["audit_anonymized"] == 1
    old_month = f"{(now - timedelta(days=395)):%Y-%m}"
    content = (paths.AUDIT_DIR / f"audit_{old_month}.jsonl").read_text()
    assert "maria" not in content and "[ANONYMIZED]" in content
