"""Certification: run component + machine probes + per-pack self-test
(+ optional model benchmark), compute enabled paths, write the signed passport.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from . import __version__, benchmark, components, machine, passport
from .detect import detect
from .guard import resolve_paths
from .packs.registry import available_locales, load_pack


def _measure(pack, th) -> dict:
    """Detection recall on the pack's own synthetic fixtures."""
    COMPAT = {
        "CNP": {"RO_CNP", "MD_IDNP"}, "IBAN": {"RO_IBAN", "MD_IBAN", "IBAN_CODE"},
        "CUI": {"RO_CUI", "MD_IDNO"}, "NAME": {"PERSON"},
        "EMAIL": {"EMAIL_ADDRESS"}, "PHONE": {"RO_PHONE", "MD_PHONE", "PHONE_NUMBER"},
        "ADDRESS": {"LOCATION"}, "BIRTHDATE": {"RO_DATE", "DATE_TIME"},
        "ORG": {"ORGANIZATION"}, "SALARY": set(),
    }
    with tempfile.TemporaryDirectory() as tmp:
        pack.generate_fixtures(seed=20260607, out_dir=Path(tmp))
        gt_dir = Path(tmp) / "ground-truth"
        per = {}
        for gt in sorted(gt_dir.glob("*.json")):
            if gt.name == "MANIFEST.json":
                continue
            meta = json.loads(gt.read_text())
            text = (Path(tmp) / meta["file"]).read_text(encoding="utf-8")
            spans = [(d.start, d.end, d.entity_type)
                     for d in detect(text, locale=pack.locale,
                                     is_csv=meta["file"].endswith(".csv"))]
            for p in meta["pii"]:
                if p["type"] == "SALARY":
                    continue
                ok_types = COMPAT.get(p["type"], set())
                needle = p["value"].split(" lei")[0]
                found, start = False, text.find(needle)
                while start != -1 and not found:
                    end = start + len(needle)
                    found = any(s < end and e > start and et in ok_types
                                for s, e, et in spans)
                    start = text.find(needle, start + 1)
                d, t = per.setdefault(p["type"], [0, 0])
                per[p["type"]] = [d + found, t + 1]
    detected = sum(d for d, _ in per.values())
    total = sum(t for _, t in per.values()) or 1
    recall = detected / total
    crit = [per.get(k, [0, 1]) for k in ("CNP", "IBAN")]
    crit_ok = all(d == t for d, t in crit)
    passed = recall >= th.get("recall_global", 0.95) and (
        crit_ok if th.get("recall_critical", 1.0) >= 1.0 else True)
    return {"self_test": "pass" if passed else "fail",
            "recall": f"{recall:.0%}", "by_type": per}


def certify(run_benchmark: bool = True, local_model: str = "gemma3:27b") -> dict:
    comp = components.run_all(local_model=local_model)
    mach = machine.run_all()

    packs_result = {}
    for locale in available_locales():
        try:
            packs_result[locale] = _measure(load_pack(locale), load_pack(locale).thresholds())
        except Exception as e:  # noqa: BLE001
            packs_result[locale] = {"self_test": "error", "error": str(e)[:120]}

    bench = None
    if run_benchmark and comp["local_model"]["ok"]:
        bench = benchmark.run(model=local_model)
        comp["local_model"]["benchmark"] = bench

    paths_enabled = resolve_paths(comp, mach, packs_result, bench)
    pp = passport.build(comp, mach, packs_result, paths_enabled, __version__)
    passport.save(pp)
    return pp
