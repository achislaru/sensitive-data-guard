"""F4/F5: tiered fail-closed path resolution + classification table."""
from sdg.classify import allowed_paths
from sdg.guard import resolve_paths

_OK = {"ok": True, "status": "ok", "detail": ""}
_FAIL = {"ok": False, "status": "fail", "detail": ""}


def _components(**over):
    base = {k: dict(_OK) for k in
            ("python", "presidio", "spacy_model", "cryptography", "ollama",
             "local_model")}
    base.update(over)
    return base


def _machine(**over):
    base = {k: dict(_OK) for k in
            ("ram", "disk", "disk_encryption", "ollama_bind", "vault_key")}
    base.update(over)
    return base


def test_all_paths_when_everything_ok():
    paths = resolve_paths(_components(), _machine(), {}, {"passed": True})
    assert paths == ["local", "cloud_pseudonymized", "cloud_direct"]


def test_disk_encryption_off_disables_all_pii_paths():
    paths = resolve_paths(_components(), _machine(disk_encryption=dict(_FAIL)),
                          {}, {"passed": True})
    assert "local" not in paths and "cloud_pseudonymized" not in paths
    assert paths == ["cloud_direct"]


def test_no_ollama_disables_only_local():
    paths = resolve_paths(_components(ollama=dict(_FAIL)), _machine(), {},
                          None)
    assert "local" not in paths
    assert "cloud_pseudonymized" in paths and "cloud_direct" in paths


def test_benchmark_fail_disables_local():
    paths = resolve_paths(_components(), _machine(), {}, {"passed": False})
    assert "local" not in paths and "cloud_pseudonymized" in paths


def test_loose_vault_key_disables_pii_paths():
    paths = resolve_paths(_components(), _machine(vault_key=dict(_FAIL)), {},
                          {"passed": True})
    assert paths == ["cloud_direct"]


def test_classification_table():
    assert allowed_paths("special_category") == ["local"]
    assert "cloud_direct" not in allowed_paths("personal_pseudonymizable")
    assert "cloud_direct" in allowed_paths("non_personal")
