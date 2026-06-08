"""Tiered fail-closed gate.

resolve_paths() turns probe results into the set of enabled processing paths,
applying the tier rules:

  * disk encryption OFF or vault key loose  -> NO PII paths at all
    (local + cloud_pseudonymized disabled; cloud_direct stays for non-PII)
  * Ollama unreachable / wrong bind / RAM too low / model benchmark fail
    -> local path disabled
  * pack self-test fail -> PII paths disabled for that locale (reported)

preflight() is what the agent calls before any sensitive task: it loads and
verifies the passport (fast checks) and returns enabled paths or a refusal.
"""
from __future__ import annotations

from . import __version__, passport

ALL_PATHS = ["local", "cloud_pseudonymized", "cloud_direct"]


def resolve_paths(components: dict, machine: dict, packs: dict,
                  benchmark: dict | None = None) -> list[str]:
    enabled = set(ALL_PATHS)

    # --- tier 1: encryption / key → gate ALL PII paths ---
    if not machine.get("disk_encryption", {}).get("ok"):
        enabled.discard("local")
        enabled.discard("cloud_pseudonymized")
    if not machine.get("vault_key", {}).get("ok"):
        enabled.discard("local")
        enabled.discard("cloud_pseudonymized")

    # --- tier 2: local-path prerequisites ---
    if not components.get("ollama", {}).get("ok"):
        enabled.discard("local")
    if not machine.get("ollama_bind", {}).get("ok"):
        enabled.discard("local")
    if not machine.get("ram", {}).get("ok"):
        enabled.discard("local")
    if not components.get("local_model", {}).get("ok"):
        enabled.discard("local")
    if benchmark is not None and not benchmark.get("passed", False):
        enabled.discard("local")

    # cloud_pseudonymized also needs a working detection stack (presidio+spacy)
    if not (components.get("presidio", {}).get("ok")
            and components.get("spacy_model", {}).get("ok")
            and components.get("cryptography", {}).get("ok")):
        enabled.discard("local")
        enabled.discard("cloud_pseudonymized")

    return [p for p in ALL_PATHS if p in enabled]


def preflight(now=None) -> dict:
    """Gate the agent calls first. Returns a structured verdict."""
    pp = passport.load()
    if pp is None:
        return {"ok": False, "reason": "no passport — run `sdg certify`",
                "paths_enabled": []}
    valid, reasons = passport.verify(pp, __version__, now=now)
    if not valid:
        return {"ok": False, "reason": "; ".join(reasons),
                "remediation": "run `sdg certify`", "paths_enabled": []}
    return {"ok": True, "paths_enabled": pp.get("paths_enabled", []),
            "expires": pp.get("expires"), "machine_id": pp.get("machine_id")}
