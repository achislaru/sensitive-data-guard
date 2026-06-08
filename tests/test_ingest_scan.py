"""F9: channel pre-gate (channel × data-class policy)."""
import pytest

import sdg.paths as paths
from sdg import channels


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "STATE_DIR", tmp_path)
    monkeypatch.setattr(paths, "QUARANTINE_DIR", tmp_path / "quarantine")
    paths.QUARANTINE_DIR.mkdir(parents=True)


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_special_category_on_telegram_is_quarantined(tmp_path):
    # a Romanian CNP makes this special_category
    f = _write(tmp_path, "id.txt", "Numele meu este Ion Popescu, CNP 1850512123454.")
    res = channels.ingest_scan(f, "telegram")
    assert res["data_class"] == "special_category"
    assert res["action"] == "quarantine"
    # file is moved out of its original location into quarantine
    assert not (tmp_path / "id.txt").exists()
    assert res["quarantined_path"]
    # an incident-candidate was logged
    incidents = (paths.QUARANTINE_DIR / "incidents.jsonl").read_text()
    assert "channel_policy_quarantine" in incidents


def test_special_category_local_channel_allowed(tmp_path):
    f = _write(tmp_path, "id.txt", "CNP 1850512123454.")
    res = channels.ingest_scan(f, "cli")
    assert res["data_class"] == "special_category"
    assert res["action"] == "allow"
    assert (tmp_path / "id.txt").exists()  # not moved


def test_non_personal_on_telegram_allowed(tmp_path):
    f = _write(tmp_path, "notes.txt", "Sedinta de luni la ora 10 despre roadmap.")
    res = channels.ingest_scan(f, "telegram")
    assert res["action"] == "allow"


def test_missing_file_allows(tmp_path):
    res = channels.ingest_scan(str(tmp_path / "nope.txt"), "telegram")
    assert res["action"] == "allow"
