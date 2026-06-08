"""Local-model capability gate.

A model being *installed* is not the same as being *capable*: the pilot found
qwen3-vl present but extracting 0/20 CNPs (mandatory thinking-mode loops),
while gemma3:27b scored 20/20. So certification runs a reduced extraction
benchmark against the pack's synthetic payroll fixture and checks the pack's
thresholds. Requires Ollama + the model; callers skip it gracefully if absent.
"""
from __future__ import annotations

import json
import re
import tempfile
import time
import urllib.request
from pathlib import Path

from .packs.registry import load_pack

OLLAMA_CHAT = "http://127.0.0.1:11434/api/chat"


def _ask(model: str, prompt: str, timeout: int = 300) -> str:
    body = json.dumps({
        "model": model, "stream": False, "think": False,
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 2000},
    }).encode()
    req = urllib.request.Request(OLLAMA_CHAT, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["message"].get("content") or ""


def run(model: str = "gemma3:27b", locale: str = "ro_RO") -> dict:
    """Returns {passed: bool, detail: {...}} or {passed: False, error: ...}."""
    pack = load_pack(locale)
    th = pack.thresholds().get("benchmark", {})
    with tempfile.TemporaryDirectory() as tmp:
        pack.generate_fixtures(seed=20260607, out_dir=Path(tmp))
        payroll = Path(tmp) / "data/payroll/payroll.csv"
        text = payroll.read_text(encoding="utf-8")
        gt_cnp = set(re.findall(r"\b\d{13}\b", text))
        gt_iban = set(re.findall(r"RO\d{2}[A-Z]{4}\d{16}", text))
        try:
            t0 = time.time()
            out = _ask(model, "Extract ALL CNPs and ALL IBANs from this payroll "
                       "CSV. Reply with two plain lists, one per line, nothing "
                       f"else.\n\n{text}")
            dt = round(time.time() - t0, 1)
        except Exception as e:
            return {"passed": False, "error": str(e)[:160]}

    got_cnp = set(re.findall(r"\b\d{13}\b", out))
    got_iban = set(re.findall(r"RO\d{2}[A-Z]{4}\d{16}", out))
    cnp_hit = len(gt_cnp & got_cnp)
    iban_hit = len(gt_iban & got_iban)
    invented = len(got_cnp - gt_cnp) + len(got_iban - gt_iban)
    detail = {
        "model": model, "duration_s": dt,
        "cnp": f"{cnp_hit}/{len(gt_cnp)}", "iban": f"{iban_hit}/{len(gt_iban)}",
        "invented": invented,
    }
    passed = (cnp_hit >= th.get("cnp_extraction", len(gt_cnp))
              and iban_hit >= th.get("iban_extraction", len(gt_iban))
              and invented <= th.get("invented_max", 0))
    return {"passed": passed, "detail": detail}
