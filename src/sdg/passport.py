"""Machine audit passport: signed JSON certifying which paths are enabled.

Signature is an HMAC with a machine-local key (0600). This is integrity /
anti-staleness for the local machine, NOT PKI — it stops a stale or
hand-edited passport from being trusted, which is the actual threat.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import platform
import uuid
from datetime import datetime, timedelta, timezone

from . import paths

SCHEMA = 1
FRESHNESS_DAYS = 30
_SIGN_KEY = paths.STATE_DIR / "passport.key"


def machine_id() -> str:
    raw = f"{platform.node()}|{uuid.getnode()}|{platform.system()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _sign_key() -> bytes:
    paths.ensure_state()
    if not _SIGN_KEY.exists():
        import os
        _SIGN_KEY.write_bytes(os.urandom(32))
        _SIGN_KEY.chmod(0o600)
    return _SIGN_KEY.read_bytes()


def _canonical(passport: dict) -> bytes:
    body = {k: v for k, v in passport.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, ensure_ascii=False).encode()


def sign(passport: dict) -> str:
    return hmac.new(_sign_key(), _canonical(passport), hashlib.sha256).hexdigest()


def build(components: dict, machine: dict, packs: dict,
          paths_enabled: list[str], sdg_version: str,
          now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    passport = {
        "schema": SCHEMA,
        "machine_id": machine_id(),
        "issued": now.isoformat(timespec="seconds"),
        "expires": (now + timedelta(days=FRESHNESS_DAYS)).isoformat(timespec="seconds"),
        "sdg_version": sdg_version,
        "components": components,
        "machine": machine,
        "packs": packs,
        "paths_enabled": paths_enabled,
    }
    passport["signature"] = sign(passport)
    return passport


def save(passport: dict) -> None:
    paths.ensure_state()
    paths.PASSPORT.write_text(json.dumps(passport, ensure_ascii=False, indent=2),
                              encoding="utf-8")


def load() -> dict | None:
    if not paths.PASSPORT.exists():
        return None
    return json.loads(paths.PASSPORT.read_text(encoding="utf-8"))


def verify(passport: dict, sdg_version: str,
           now: datetime | None = None) -> tuple[bool, list[str]]:
    """Returns (valid, reasons_if_invalid). Fast checks only (no benchmark)."""
    now = now or datetime.now(timezone.utc)
    reasons = []
    if passport.get("schema") != SCHEMA:
        reasons.append("schema mismatch")
    expected = hmac.new(_sign_key(), _canonical(passport), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, passport.get("signature", "")):
        reasons.append("signature invalid (tampered or different machine)")
    if passport.get("machine_id") != machine_id():
        reasons.append("machine_id mismatch")
    try:
        if datetime.fromisoformat(passport["expires"]) < now:
            reasons.append("expired (re-certify)")
    except (KeyError, ValueError):
        reasons.append("missing/invalid expiry")
    if passport.get("sdg_version") != sdg_version:
        reasons.append(f"sdg version changed ({passport.get('sdg_version')} "
                       f"!= {sdg_version}); re-certify")
    return (not reasons, reasons)
