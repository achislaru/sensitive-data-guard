"""Compliance linter — layers 1 (structural) and 2 (semantic).

A protocol can only NARROW the baseline, never widen it. Layer 1 uses the JSON
Schema (illegal states unrepresentable). Layer 2 adds semantic checks that need
logic beyond schema shape. Returns (errors, warnings); errors block activation.
"""
from __future__ import annotations

import re

import jsonschema

from ..classify import DATA_CLASS_PATHS
from ..packs.registry import available_locales
from .loader import schema

_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
_ART22_CATEGORIES = {"hr_recruitment", "credit", "discipline", "performance"}


def _structural(protocol: dict) -> list[str]:
    try:
        jsonschema.validate(protocol, schema())
        return []
    except jsonschema.ValidationError as e:
        path = "/".join(str(p) for p in e.absolute_path) or "(root)"
        return [f"structural: {path}: {e.message}"]


def _semantic(protocol: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    data_class = protocol.get("classification", {}).get("data_class")
    required_path = protocol.get("required_path")
    baseline = DATA_CLASS_PATHS.get(data_class, [])

    # path must be within the classification baseline (more restrictive only)
    if required_path and required_path not in baseline:
        errors.append(
            f"required_path '{required_path}' exceeds baseline for "
            f"data_class '{data_class}' (allowed: {baseline})")

    steps = protocol.get("steps", [])
    ops = [s["op"] for s in steps]
    prompts = protocol.get("prompts", {}) or {}

    # ai_cloud requires a non-local path and a non-empty cloud prompt set
    if "ai_cloud" in ops:
        if required_path == "local":
            errors.append("ai_cloud step on a local-only protocol")
        if not prompts.get("cloud"):
            errors.append("ai_cloud step but prompts.cloud is empty")
    if "ai_local" in ops and not prompts.get("local"):
        errors.append("ai_local step but prompts.local is empty")

    # restore must come after pseudonymize
    if "restore" in ops and ("pseudonymize" not in ops
                             or ops.index("restore") < ops.index("pseudonymize")):
        errors.append("restore step without a preceding pseudonymize")

    # locale_scope is the protocol's DECLARED support, not a per-machine
    # install requirement: error only if NONE is installed here; warn per gap.
    installed = set(available_locales())
    scope = protocol.get("locale_scope", [])
    if scope and not (set(scope) & installed):
        errors.append(f"none of locale_scope {scope} is installed on this machine")
    for loc in scope:
        if loc not in installed:
            warnings.append(f"locale '{loc}' declared but not installed here")

    # prompt placeholders must be input roles or declared params
    roles = {i["role"] for i in protocol.get("inputs", [])}
    params = set(protocol.get("params", []))
    known = roles | params
    for path_group in ("local", "cloud"):
        for name, tmpl in (prompts.get(path_group) or {}).items():
            for ph in _PLACEHOLDER.findall(tmpl):
                if ph not in known:
                    errors.append(
                        f"prompt {path_group}.{name}: undeclared placeholder "
                        f"'{{{{{ph}}}}}' (add to inputs or params)")

    # output schema refs resolvable
    schemas = protocol.get("schemas", {}) or {}
    for s in steps:
        ref = s.get("output_schema_ref")
        if ref and ref not in schemas:
            errors.append(f"step '{s['id']}': output_schema_ref '{ref}' not in schemas")

    # contains_pii true is only safe to leave the pipeline if local-only handling
    if protocol.get("output", {}).get("contains_pii") and required_path != "local":
        errors.append("output.contains_pii true on a non-local path")

    # Art. 22 heuristic
    cat = protocol.get("audit", {}).get("category")
    if cat in _ART22_CATEGORIES and not protocol.get("hitl", {}).get("art22_decision"):
        warnings.append(
            f"audit category '{cat}' usually implies an Art. 22 decision; "
            f"consider hitl.art22_decision: true")

    return errors, warnings


def validate(protocol: dict) -> tuple[list[str], list[str]]:
    structural = _structural(protocol)
    if structural:
        # structural failures make semantic analysis unreliable
        return structural, []
    return _semantic(protocol)
