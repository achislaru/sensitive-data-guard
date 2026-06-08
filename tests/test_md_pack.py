"""F7: Moldova (md_MD) country pack — validators, detection recall, routing.

Mirrors the ro_RO recall test: global >= 95%, critical (IDNP + IBAN) = 100%.
md_MD shares the Romanian spaCy model but ships its own identifiers.
"""
import json
from pathlib import Path

from sdg.classify import classify_text
from sdg.detect import detect
from sdg.packs.md_MD.validators import idnp_valid, idno_valid, iban_md_valid
from sdg.packs.registry import available_locales, load_pack

# ground-truth type -> Presidio types that count as a detection
COMPATIBLE = {
    "IDNP": {"MD_IDNP"},
    "IDNO": {"MD_IDNO"},
    "IBAN": {"MD_IBAN", "IBAN_CODE"},
    "NAME": {"PERSON"},
    "EMAIL": {"EMAIL_ADDRESS"},
    "PHONE": {"MD_PHONE", "PHONE_NUMBER"},
    "ADDRESS": {"LOCATION"},
    "BIRTHDATE": {"MD_DATE", "DATE_TIME"},
    "ORG": {"ORGANIZATION"},
    "SALARY": set(),
}


def test_pack_registered():
    assert "md_MD" in available_locales()
    assert load_pack("md_MD").locale == "md_MD"


def test_certify_self_test_passes_for_both_packs():
    # regression: certify._measure must recognize each pack's own ground-truth
    # type names (md_MD emits IDNP/IDNO/MD_DATE, not CNP/CUI/RO_DATE) and derive
    # the critical set from the pack, not a hardcoded ("CNP","IBAN").
    from sdg import certify
    for loc in ("ro_RO", "md_MD"):
        p = load_pack(loc)
        res = certify._measure(p, p.thresholds())
        assert res["self_test"] == "pass", f"{loc}: {res}"


def test_validators_check_digits():
    # a known self-consistent IDNP from the generator algorithm
    from sdg.packs.md_MD.validators import _idn_control
    body = "200001011234"
    good = body + _idn_control(body)
    assert idnp_valid(good)
    assert idno_valid(good)              # same checksum
    # flip the control digit -> rejected
    bad = body + str((int(good[-1]) + 1) % 10)
    assert not idnp_valid(bad)
    assert not idnp_valid("12345")       # wrong length
    assert not iban_md_valid("MD00AB000000000000000000")  # bad mod-97


def test_idnp_forces_special_category():
    from sdg.packs.md_MD.validators import _idn_control
    body = "200001011234"
    idnp = body + _idn_control(body)
    res = classify_text(f"IDNP-ul meu este {idnp}.", locale="md_MD")
    assert res["data_class"] == "special_category"
    assert res["allowed_paths"] == ["local"]


def _measure(out_dir: Path):
    pack = load_pack("md_MD")
    pack.generate_fixtures(seed=20260608, out_dir=out_dir)
    gt_dir = out_dir / "ground-truth"
    per_type, misses = {}, []
    for gt_file in sorted(gt_dir.glob("*.json")):
        if gt_file.name == "MANIFEST.json":
            continue
        meta = json.loads(gt_file.read_text())
        text = (out_dir / meta["file"]).read_text(encoding="utf-8")
        is_csv = meta["file"].endswith(".csv")
        spans = [(d.start, d.end, d.entity_type)
                 for d in detect(text, locale="md_MD", is_csv=is_csv)]
        for p in meta["pii"]:
            t, v = p["type"], p["value"]
            if t == "SALARY":
                continue
            ok_types = COMPATIBLE.get(t, set())
            needle = v.split(" lei")[0]
            found, start = False, text.find(needle)
            while start != -1 and not found:
                end = start + len(needle)
                found = any(s < end and e > start and et in ok_types
                            for s, e, et in spans)
                start = text.find(needle, start + 1)
            d, tot = per_type.setdefault(t, [0, 0])
            per_type[t] = [d + found, tot + 1]
            if not found:
                misses.append((meta["file"], t, v))
    return per_type, misses


def test_recall_thresholds(tmp_path):
    per_type, misses = _measure(tmp_path)
    detected = sum(d for d, _ in per_type.values())
    total = sum(t for _, t in per_type.values())
    recall = detected / total
    idnp = per_type.get("IDNP", [0, 1])
    iban = per_type.get("IBAN", [0, 1])
    assert idnp[0] == idnp[1], f"IDNP recall {idnp} != 100%"
    assert iban[0] == iban[1], f"IBAN recall {iban} != 100%"
    assert recall >= 0.95, f"global recall {recall:.1%} < 95%; misses={misses[:10]}"
