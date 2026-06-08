"""F8: protocol schema, the no-special-to-cloud invariant, linter, dryrun."""
import copy

import pytest

from sdg.protocols import engine, linter, loader


def _all_builtins():
    return [loader.load(pid) for pid, e in loader.list_protocols().items()
            if e["source"] == "builtin"]


def test_all_builtins_validate():
    for p in _all_builtins():
        errors, _ = linter.validate(p)
        assert not errors, f"{p['id']}: {errors}"


def test_builtin_count_and_ids():
    ids = {p["id"] for p in _all_builtins()}
    assert {"hr-cv-screening", "invoice-processing", "payroll-analysis",
            "contract-review", "expense-reconciliation",
            "gdpr-subject-request"} <= ids


def test_special_category_cannot_reach_cloud_structural():
    """The load-bearing invariant: a special-category protocol routed to a
    cloud path must be REJECTED (structural layer)."""
    p = copy.deepcopy(loader.load("payroll-analysis"))  # special_category
    p["required_path"] = "cloud_pseudonymized"
    errors, _ = linter.validate(p)
    assert errors, "special-category → cloud must be rejected"
    assert any("required_path" in e for e in errors)


def test_special_category_cannot_reach_cloud_direct():
    p = copy.deepcopy(loader.load("hr-cv-screening"))
    p["required_path"] = "cloud_direct"
    errors, _ = linter.validate(p)
    assert errors


def test_ai_cloud_requires_cloud_prompt():
    p = copy.deepcopy(loader.load("invoice-processing"))
    p["prompts"]["cloud"] = {}  # empty cloud prompts
    errors, _ = linter.validate(p)
    assert any("cloud" in e for e in errors)


def test_undeclared_placeholder_rejected():
    p = copy.deepcopy(loader.load("hr-cv-screening"))
    p["prompts"]["local"]["score_local"] += " {{undeclared_var}}"
    errors, _ = linter.validate(p)
    assert any("undeclared placeholder" in e for e in errors)


@pytest.mark.parametrize("pid", [
    "hr-cv-screening", "invoice-processing", "payroll-analysis",
    "contract-review", "expense-reconciliation", "gdpr-subject-request"])
def test_dryrun_all_builtins(pid):
    res = engine.dryrun(pid, locale="ro_RO")
    assert res["ok"], res
    assert res.get("detection") == "ok"
    # cloud protocols must prove zero critical PII left the machine
    p = loader.load(pid)
    if p["required_path"] == "cloud_pseudonymized":
        assert res.get("outbound_clean") == "ok", res
