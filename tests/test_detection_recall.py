"""F5 (started in F1): detection recall on synthetic fixtures.

Reproduces the pilot's 100% recall result: global >= 95%, critical = 100%.
Generates fixtures deterministically into a tmp dir, then measures detection
against the ground-truth lists.
"""
import json
from pathlib import Path

import pytest

from sdg.detect import detect
from sdg.packs.registry import load_pack

# ground-truth type -> Presidio types that count as a detection
COMPATIBLE = {
    "CNP": {"RO_CNP"},
    "IBAN": {"RO_IBAN", "IBAN_CODE"},
    "CUI": {"RO_CUI"},
    "NAME": {"PERSON"},
    "EMAIL": {"EMAIL_ADDRESS"},
    "PHONE": {"RO_PHONE", "PHONE_NUMBER"},
    "ADDRESS": {"LOCATION"},
    "BIRTHDATE": {"RO_DATE", "DATE_TIME"},
    "ORG": {"ORGANIZATION"},
    "SALARY": set(),  # out of scope for automatic detection
}


def _measure(out_dir: Path):
    pack = load_pack("ro_RO")
    pack.generate_fixtures(seed=20260607, out_dir=out_dir)
    gt_dir = out_dir / "ground-truth"
    per_type = {}
    misses = []
    for gt_file in sorted(gt_dir.glob("*.json")):
        if gt_file.name == "MANIFEST.json":
            continue
        meta = json.loads(gt_file.read_text())
        text = (out_dir / meta["file"]).read_text(encoding="utf-8")
        is_csv = meta["file"].endswith(".csv")
        spans = [(d.start, d.end, d.entity_type)
                 for d in detect(text, locale="ro_RO", is_csv=is_csv)]
        for p in meta["pii"]:
            t, v = p["type"], p["value"]
            if t == "SALARY":
                continue
            ok_types = COMPATIBLE.get(t, set())
            needle = v.split(" lei")[0]
            found = False
            start = text.find(needle)
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
    cnp = per_type.get("CNP", [0, 1])
    iban = per_type.get("IBAN", [0, 1])
    assert cnp[0] == cnp[1], f"CNP recall {cnp} != 100%"
    assert iban[0] == iban[1], f"IBAN recall {iban} != 100%"
    assert recall >= 0.95, f"global recall {recall:.1%} < 95%; misses={misses[:10]}"
