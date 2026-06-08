"""Protocol execution engine — a deterministic state machine over the
validated primitives (detect / pseudonymize / restore / audit).

The CLI drives it: `run` executes up to the first AI step and emits a STEP
directive (JSON) for the agent; the agent runs the model and calls `resume`
with the output. The deterministic guarantees (detection, the unconditional
outbound re-scan inside pseudonymize, schema validation, audit) live here —
the LLM only generates the ai_* response from a rendered, already-pseudonymized
prompt. `dryrun` exercises the whole machine headless against synthetic
fixtures with the AI step stubbed.
"""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

import jsonschema

from .. import audit, paths
from ..classify import DATA_CLASS_PATHS
from ..detect import detect
from ..packs.registry import load_pack
from ..pipeline import pseudonymize
from ..vault import Vault
from . import linter
from .loader import load as load_protocol

_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

# required_path -> audit path enum (they coincide)
_AUDIT_PATH = {"local": "local", "cloud_pseudonymized": "cloud_pseudonymized",
               "cloud_direct": "cloud_direct"}


class ProtocolError(RuntimeError):
    pass


def _state_path(session: str) -> Path:
    paths.ensure_state()
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session)
    return paths.SESSIONS_DIR / f"{safe}.proto.json"


def _vault(session: str, locale: str) -> Vault:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session)
    return Vault(db=paths.SESSIONS_DIR / f"{safe}.db", key=paths.VAULT_KEY,
                 label_map=load_pack(locale).label_map)


def _render(template: str, mapping: dict) -> str:
    return _PLACEHOLDER.sub(lambda m: str(mapping.get(m.group(1), m.group(0))),
                            template)


def _check_lint(protocol: dict):
    errors, _ = linter.validate(protocol)
    if errors:
        raise ProtocolError("protocol failed validation: " + "; ".join(errors))


def run(protocol_id: str, text: str, session: str, *, locale: str = "ro_RO",
        params: dict | None = None, is_csv: bool = False,
        user: str = "agent", source_channel: str = "cli") -> dict:
    """Execute up to the first ai_* step. Returns a STEP directive or a
    completed result (if the protocol has no AI step)."""
    protocol = load_protocol(protocol_id)
    _check_lint(protocol)
    if locale not in protocol["locale_scope"]:
        raise ProtocolError(
            f"locale {locale} not in protocol locale_scope {protocol['locale_scope']}")
    params = params or {}
    required_path = protocol["required_path"]
    vault = _vault(session, locale)

    working = text
    pii_types: dict = {}
    for idx, step in enumerate(protocol["steps"]):
        op = step["op"]
        if op == "detect":
            for d in detect(working, locale=locale, is_csv=is_csv):
                pii_types[d.entity_type] = pii_types.get(d.entity_type, 0) + 1
        elif op == "pseudonymize":
            working = pseudonymize(working, vault, locale=locale, is_csv=is_csv)
        elif op in ("ai_local", "ai_cloud"):
            group = "local" if op == "ai_local" else "cloud"
            tmpl = protocol["prompts"][group][step["prompt_ref"]]
            mapping = dict(params)
            for inp in protocol["inputs"]:
                mapping.setdefault(inp["role"], working)
            prompt = _render(tmpl, mapping)
            state = {
                "protocol_id": protocol_id, "locale": locale,
                "required_path": required_path, "resume_step": idx + 1,
                "expects_output": step.get("expects_output", "text"),
                "output_schema_ref": step.get("output_schema_ref"),
                "schemas": protocol.get("schemas", {}),
                "steps": protocol["steps"],
                "output": protocol["output"], "audit": protocol["audit"],
                "hitl": protocol["hitl"], "pii_types": pii_types,
                "user": user, "source_channel": source_channel,
            }
            _state_path(session).write_text(json.dumps(state), encoding="utf-8")
            return {"status": "need_ai", "action": op, "prompt": prompt,
                    "expects": step.get("expects_output", "text"),
                    "output_schema_ref": step.get("output_schema_ref"),
                    "session": session}
        elif op == "restore":
            working = vault.restore(working)
        elif op == "emit":
            pass
    # no AI step: finalize immediately
    return _finalize(protocol_id, locale, required_path, working,
                     protocol["steps"], protocol["output"], protocol["audit"],
                     protocol["hitl"], pii_types, user, source_channel)


def resume(session: str, ai_output: str, *, audit_log: bool = True) -> dict:
    sp = _state_path(session)
    if not sp.exists():
        raise ProtocolError(f"no pending protocol state for session {session}")
    st = json.loads(sp.read_text(encoding="utf-8"))

    # validate AI output schema if declared
    ref = st.get("output_schema_ref")
    if st.get("expects_output") == "json" and ref:
        schema = st["schemas"].get(ref)
        try:
            obj = json.loads(ai_output)
        except json.JSONDecodeError as e:
            raise ProtocolError(f"ai output is not valid JSON: {e}")
        if schema:
            try:
                jsonschema.validate(obj, schema)
            except jsonschema.ValidationError as e:
                raise ProtocolError(f"ai output fails schema '{ref}': {e.message}")

    vault = _vault(session, st["locale"])
    working = ai_output
    for step in st["steps"][st["resume_step"]:]:
        if step["op"] == "restore":
            working = vault.restore(working)
        elif step["op"] == "emit":
            pass
    result = _finalize(st["protocol_id"], st["locale"], st["required_path"],
                       working, st["steps"], st["output"], st["audit"],
                       st["hitl"], st["pii_types"], st["user"],
                       st["source_channel"], audit_log=audit_log)
    sp.unlink(missing_ok=True)
    return result


def _finalize(protocol_id, locale, required_path, output_text, steps, output,
              audit_cfg, hitl, pii_types, user, source_channel,
              audit_log: bool = True) -> dict:
    if audit_log:
        audit.log_interaction(
            user, audit_cfg["category"], _AUDIT_PATH[required_path],
            pii_types, source_channel=source_channel, protocol_id=protocol_id)
    res = {"status": "done", "protocol_id": protocol_id, "output": output_text,
           "destination": output["destination"]}
    if hitl.get("art22_decision"):
        res["hitl"] = hitl.get("gate_message",
                               "This output is decision support; a human decides.")
    return res


# ----------------------------------------------------------------- dryrun

def _stub_from_schema(schema: dict):
    t = schema.get("type")
    if t == "object":
        return {k: _stub_from_schema(v)
                for k, v in schema.get("properties", {}).items()
                if k in schema.get("required", schema.get("properties", {}).keys())}
    return {"integer": 0, "number": 0, "string": "stub", "boolean": False,
            "array": [], "object": {}}.get(t, "stub")


_DRYRUN_FILE = {"csv": "data/payroll/payroll.csv",
                "invoice": "data/invoices/invoice_01.txt",
                "cv": "data/cv/cv_03.txt"}


def dryrun(protocol_id: str, locale: str = "ro_RO") -> dict:
    """Headless end-to-end check against synthetic fixtures; AI step stubbed."""
    protocol = load_protocol(protocol_id)
    errors, warnings = linter.validate(protocol)
    if errors:
        return {"ok": False, "stage": "validate", "errors": errors}

    formats = protocol["inputs"][0].get("formats", [])
    is_csv = "csv" in formats or "xlsx" in formats
    checks = {"validate": "ok", "warnings": warnings}

    with tempfile.TemporaryDirectory() as tmp:
        load_pack(locale).generate_fixtures(seed=20260607, out_dir=Path(tmp))
        if is_csv:
            sample = Path(tmp) / _DRYRUN_FILE["csv"]
        elif "invoice" in protocol_id or "expense" in protocol_id:
            sample = Path(tmp) / _DRYRUN_FILE["invoice"]
        else:
            sample = Path(tmp) / _DRYRUN_FILE["cv"]
        text = sample.read_text(encoding="utf-8")

        session = f"dryrun-{protocol_id}"
        params = {p: f"<{p}>" for p in protocol.get("params", [])}
        try:
            step1 = run(protocol_id, text, session, locale=locale, params=params,
                        is_csv=is_csv, user="dryrun")
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "stage": "run", "error": str(e)[:200], **checks}

        if step1["status"] == "need_ai":
            checks["detection"] = "ok"
            # for cloud steps, verify the outbound prompt carries no critical PII
            if step1["action"] == "ai_cloud":
                crit = load_pack(locale).critical_entities()
                leaked = [d for d in detect(step1["prompt"], locale=locale)
                          if d.entity_type in crit]
                checks["outbound_clean"] = "ok" if not leaked else "FAIL"
                if leaked:
                    return {"ok": False, "stage": "outbound_scan", **checks}
            else:
                checks["outbound_clean"] = "n/a (local)"
            # build a stub AI output
            ref = step1.get("output_schema_ref")
            if step1["expects"] == "json" and ref:
                stub = json.dumps(_stub_from_schema(protocol["schemas"][ref]))
            elif step1["action"] == "ai_cloud":
                stub = step1["prompt"]  # echo pseudonymized text → exercises restore
            else:
                stub = "stub local analysis output"
            try:
                final = resume(session, stub, audit_log=False)
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "stage": "resume", "error": str(e)[:200],
                        **checks}
            checks["schema"] = "ok"
            checks["completed"] = "ok"
        else:
            checks["detection"] = "ok"
            checks["completed"] = "ok"
        # clean any leftover dryrun vault/state
        for suffix in (".db", ".proto.json"):
            f = paths.SESSIONS_DIR / f"{re.sub(r'[^A-Za-z0-9_-]', '_', session)}{suffix}"
            f.unlink(missing_ok=True)

    return {"ok": True, **checks}
