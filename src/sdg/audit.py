"""Audit trail (types-only) + retention.

Monthly JSONL at STATE/audit/audit_YYYY-MM.jsonl. Each AI interaction with
personal data is one line: timestamp, user, data category, path
(local/cloud_pseudonymized/cloud_direct), source_channel, pii_types
(TYPES + counts ONLY — never values, else the log itself leaks), protocol_id,
source file (name only), model, duration.

Retention (run from cron):
  * conversations/results > 90 days -> delete
  * audit entries > 12 months       -> anonymize (drop user, keep stats)
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import paths

RETENTION_CONV_DAYS = 90
RETENTION_AUDIT_MONTHS = 12

VALID_PATHS = {"local", "cloud_pseudonymized", "cloud_direct"}
VALID_CHANNELS = {"cli", "telegram", "slack", "other"}


def log_interaction(user: str, data_category: str, path: str,
                    pii_types: dict, *, source_channel: str = "cli",
                    protocol_id: str = "", source_file: str = "",
                    model: str = "", duration_s: float = 0,
                    now: datetime | None = None) -> Path:
    """Append an audit entry. pii_types = {'RO_CNP': 20, 'PERSON': 20}."""
    assert path in VALID_PATHS, f"unknown path: {path}"
    assert source_channel in VALID_CHANNELS, f"unknown channel: {source_channel}"
    # anti-leak guard: pii_types values MUST be counts, never values
    assert all(isinstance(v, int) for v in pii_types.values()), \
        "pii_types must contain ONLY counts, not values"
    now = now or datetime.now(timezone.utc)
    paths.AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    f = paths.AUDIT_DIR / f"audit_{now:%Y-%m}.jsonl"
    entry = {
        "timestamp": now.isoformat(timespec="seconds"),
        "user": user,
        "data_category": data_category,
        "path": path,
        "source_channel": source_channel,
        "protocol_id": protocol_id,
        "pii_types": pii_types,
        "source_file": Path(source_file).name if source_file else "",
        "model": model,
        "duration_s": duration_s,
    }
    with f.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return f


def apply_retention(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    report = {"conversations_deleted": 0, "audit_anonymized": 0}

    conv_cutoff = now - timedelta(days=RETENTION_CONV_DAYS)
    if paths.CONV_DIR.exists():
        for f in paths.CONV_DIR.iterdir():
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime < conv_cutoff:
                f.unlink()
                report["conversations_deleted"] += 1

    audit_cutoff = now - timedelta(days=RETENTION_AUDIT_MONTHS * 30)
    if paths.AUDIT_DIR.exists():
        for f in paths.AUDIT_DIR.glob("audit_*.jsonl"):
            lines, changed = [], False
            for line in f.read_text(encoding="utf-8").splitlines():
                e = json.loads(line)
                ts = datetime.fromisoformat(e["timestamp"])
                if ts < audit_cutoff and e.get("user") != "[ANONYMIZED]":
                    e["user"] = "[ANONYMIZED]"
                    changed = True
                    report["audit_anonymized"] += 1
                lines.append(json.dumps(e, ensure_ascii=False))
            if changed:
                f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def monthly_summary(month: str) -> dict:
    f = paths.AUDIT_DIR / f"audit_{month}.jsonl"
    if not f.exists():
        return {"month": month, "interactions": 0}
    entries = [json.loads(l) for l in f.read_text().splitlines()]
    return {
        "month": month,
        "interactions": len(entries),
        "by_path": dict(Counter(e["path"] for e in entries)),
        "by_channel": dict(Counter(e.get("source_channel", "?") for e in entries)),
        "by_protocol": dict(Counter(e.get("protocol_id", "") for e in entries)),
        "by_category": dict(Counter(e["data_category"] for e in entries)),
    }
