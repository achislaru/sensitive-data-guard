#!/usr/bin/env python3
"""UserPromptSubmit hook: channel pre-gate for inbound attachments.

Optional, transport-agnostic. Reads the harness hook payload (JSON on stdin),
finds file paths referenced in the prompt, infers the source channel from the
path (telegram-images/ -> telegram, slack-files/ -> slack, else cli), and runs
`sdg ingest-scan` on each. If any file is quarantined (special-category data on
a remote channel), it blocks the turn with the remediation message; if any is a
warning, it injects that as additional context.

Install (Claude Code settings.json):
  "hooks": { "UserPromptSubmit": [
    { "hooks": [ { "type": "command",
        "command": "python3 ~/.claude/skills/sensitive-data-guard/hooks/ingest_scan.py" } ] }
  ] }

This hook NEVER blocks on its own errors — a failure degrades to allow, so it
can't wedge the agent. The CLI/protocol layer remains the authoritative guard.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# crude path token finder: things that look like file paths in the prompt
_PATH = re.compile(r"[~./\w-]+/[\w./-]+\.\w+")


def _channel_for(path: str) -> str:
    if "telegram-images" in path or "telegram" in path:
        return "telegram"
    if "slack-files" in path or "slack" in path:
        return "slack"
    return "cli"


def _sdg() -> str | None:
    return shutil.which("sdg")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # no payload → nothing to do
    prompt = payload.get("prompt", "") or payload.get("user_prompt", "")
    sdg = _sdg()
    if not sdg or not prompt:
        return 0

    candidates = {m.group(0) for m in _PATH.finditer(prompt)}
    blocks, warns = [], []
    for raw in candidates:
        path = str(Path(raw).expanduser())
        if not Path(path).exists():
            continue
        channel = _channel_for(raw)
        if channel == "cli":
            continue  # only gate remote-channel attachments
        try:
            out = subprocess.run([sdg, "ingest-scan", "--file", path,
                                  "--channel", channel],
                                 capture_output=True, text=True, timeout=60)
            res = json.loads(out.stdout or "{}")
        except Exception:
            continue  # fail-open on hook errors; CLI guard still protects
        if res.get("action") == "quarantine":
            blocks.append(f"{Path(path).name}: {res.get('message', 'quarantined')}")
        elif res.get("action") == "warn":
            warns.append(f"{Path(path).name}: {res.get('message', 'warning')}")

    if blocks:
        print(json.dumps({
            "decision": "block",
            "reason": ("sensitive-data-guard quarantined inbound file(s):\n- "
                       + "\n- ".join(blocks)
                       + "\nProcess locally only after explicit user confirmation.")
        }))
        return 0
    if warns:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ("sensitive-data-guard channel warnings:\n- "
                                  + "\n- ".join(warns))}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
