"""Software component probes.

Each probe returns a dict: {ok: bool, status: "ok"|"warn"|"fail", detail: str,
remediation: str}. Never degrades silently — a failure carries the exact fix.
"""
from __future__ import annotations

import json
import shutil
import sys
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434"


def _r(ok, status, detail, remediation=""):
    return {"ok": ok, "status": status, "detail": detail, "remediation": remediation}


def check_python() -> dict:
    v = sys.version_info
    if (v.major, v.minor) >= (3, 11):
        return _r(True, "ok", f"Python {v.major}.{v.minor}.{v.micro}")
    return _r(False, "fail", f"Python {v.major}.{v.minor}",
              "install Python >= 3.11")


def check_presidio() -> dict:
    try:
        import presidio_analyzer  # noqa: F401
        import presidio_anonymizer  # noqa: F401
        return _r(True, "ok", "presidio-analyzer + anonymizer importable")
    except ImportError as e:
        return _r(False, "fail", f"presidio missing: {e}",
                  "pip install presidio-analyzer presidio-anonymizer")


def check_spacy_model(model: str = "ro_core_news_lg") -> dict:
    try:
        import spacy
        nlp = spacy.load(model)
        meta = getattr(nlp, "meta", {})
        return _r(True, "ok", f"{model} {meta.get('version', '?')}")
    except Exception as e:
        return _r(False, "fail", f"spaCy model {model} not loadable: {e}",
                  f"python -m spacy download {model}")


def check_cryptography() -> dict:
    try:
        from cryptography.fernet import Fernet  # noqa: F401
        return _r(True, "ok", "cryptography/Fernet importable")
    except ImportError:
        return _r(False, "fail", "cryptography missing", "pip install cryptography")


def _ollama_get(path: str, timeout: float = 3.0):
    with urllib.request.urlopen(OLLAMA_URL + path, timeout=timeout) as r:
        return json.loads(r.read())


def check_ollama() -> dict:
    try:
        data = _ollama_get("/api/tags")
        n = len(data.get("models", []))
        return _r(True, "ok", f"Ollama reachable on 127.0.0.1:11434 ({n} models)")
    except Exception as e:
        return _r(False, "warn",
                  f"Ollama not reachable on 127.0.0.1:11434 ({e})",
                  "start Ollama (local path will be disabled without it)")


def check_local_model(model: str = "gemma3:27b") -> dict:
    try:
        data = _ollama_get("/api/tags")
        for m in data.get("models", []):
            if m.get("name") == model or m.get("name", "").startswith(model):
                digest = (m.get("digest") or "")[:12]
                return _r(True, "ok", f"{model} present (digest {digest})")
        return _r(False, "warn", f"model {model} not pulled",
                  f"ollama pull {model}")
    except Exception as e:
        return _r(False, "warn", f"cannot query models ({e})", "start Ollama")


def model_digest(model: str = "gemma3:27b") -> str:
    try:
        data = _ollama_get("/api/tags")
        for m in data.get("models", []):
            if m.get("name", "").startswith(model):
                return m.get("digest", "")[:16]
    except Exception:
        pass
    return ""


def run_all(spacy_model: str = "ro_core_news_lg",
            local_model: str = "gemma3:27b") -> dict:
    return {
        "python": check_python(),
        "presidio": check_presidio(),
        "spacy_model": check_spacy_model(spacy_model),
        "cryptography": check_cryptography(),
        "ollama": check_ollama(),
        "local_model": check_local_model(local_model),
    }
