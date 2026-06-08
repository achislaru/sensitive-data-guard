"""Channel pre-gate: channel × data-class policy.

When a file arrives through a transport like Telegram, the data has ALREADY
left the user's device (it transited the provider's servers). The skill cannot
undo that — it is a *channel* risk, handled by policy here:

  * non_personal             → allow on any channel
  * personal_pseudonymizable → warn on remote channels (Telegram/Slack)
  * special_category         → QUARANTINE on remote channels + alert + DPIA
                               incident-candidate; local processing only after
                               explicit user confirmation.

The transport in cortextOS is a "dumb pipe" (it never calls a cloud AI itself),
so this gate plus the pipeline remain the actual gatekeepers for the AI step.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import paths
from .classify import classify_text

REMOTE_CHANNELS = {"telegram", "slack"}

# (data_class, is_remote) -> action
POLICY = {
    ("non_personal", True): "allow",
    ("non_personal", False): "allow",
    ("personal_pseudonymizable", True): "warn",
    ("personal_pseudonymizable", False): "allow",
    ("special_category", True): "quarantine",
    ("special_category", False): "allow",
}

_ALERT = ("This channel is not approved for special-category data "
          "(national IDs, payroll, health). The file has been quarantined. "
          "If you confirm explicitly, it can be processed LOCALLY only.")


def _log_incident(file_name: str, channel: str, data_class: str) -> None:
    paths.ensure_state()
    f = paths.QUARANTINE_DIR / "incidents.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": "channel_policy_quarantine",
        "file": Path(file_name).name,
        "channel": channel,
        "data_class": data_class,
        "note": "DPIA incident-candidate (Art. 33 assessment, not auto-notification)",
    }
    with f.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def ingest_scan(file_path: str, channel: str, *, locale: str = "ro_RO") -> dict:
    """Classify an inbound file and apply the channel policy.

    Returns {action, data_class, message, ...}. action ∈ allow|warn|quarantine.
    """
    channel = channel.lower()
    is_remote = channel in REMOTE_CHANNELS
    p = Path(file_path)
    if not p.exists():
        return {"action": "allow", "data_class": "unknown",
                "message": f"file not found: {file_path}"}

    is_csv = p.suffix.lower() in (".csv", ".tsv")
    try:
        text = p.read_text(encoding="utf-8")
        cls = classify_text(text, locale=locale, is_csv=is_csv)
        data_class = cls["data_class"]
    except (UnicodeDecodeError, ValueError):
        # binary (pdf/docx/image): cannot scan content here
        if is_remote:
            return {"action": "warn", "data_class": "unscanned-binary",
                    "message": ("binary attachment from a remote channel could "
                                "not be scanned; verify it carries no "
                                "special-category data before cloud processing")}
        return {"action": "allow", "data_class": "unscanned-binary",
                "message": "binary; not scanned (local channel)"}

    action = POLICY[(data_class, is_remote)]
    result = {"action": action, "data_class": data_class,
              "channel": channel, "pii_types": cls["pii_types"]}

    if action == "quarantine":
        paths.ensure_state()
        dest = paths.QUARANTINE_DIR / p.name
        try:
            shutil.move(str(p), str(dest))
            result["quarantined_path"] = str(dest)
        except OSError as e:
            result["quarantined_path"] = None
            result["move_error"] = str(e)
        _log_incident(p.name, channel, data_class)
        result["message"] = _ALERT
    elif action == "warn":
        result["message"] = (f"personal data on a remote channel ({channel}); "
                             "pseudonymization required before any cloud step")
    else:
        result["message"] = "ok"
    return result
