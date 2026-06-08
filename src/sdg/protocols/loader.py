"""Protocol discovery and loading.

Built-in protocols ship read-only in the package. User protocols live in
~/.config/sdg/protocols and SHADOW built-ins with the same id. A content
checksum lets `import`/`activate` detect changed files and force re-validation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from .. import paths

BUILTIN_DIR = Path(__file__).parent / "builtin"
SCHEMA_PATH = Path(__file__).parent / "schema.json"
TEMPLATE_PATH = Path(__file__).parent / "_template.yaml"


def user_dir() -> Path:
    d = paths.CONFIG_DIR / "protocols"
    d.mkdir(parents=True, exist_ok=True)
    return d


def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_file(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def checksum(protocol: dict) -> str:
    canonical = json.dumps(protocol, sort_keys=True, ensure_ascii=False).encode()
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def list_protocols() -> dict:
    """id -> {source: builtin|user, path, version}. User shadows builtin."""
    out = {}
    for f in sorted(BUILTIN_DIR.glob("*.yaml")):
        p = load_file(f)
        out[p["id"]] = {"source": "builtin", "path": str(f),
                        "version": p.get("version"), "name": p.get("name")}
    for f in sorted(user_dir().glob("*.yaml")):
        p = load_file(f)
        out[p["id"]] = {"source": "user", "path": str(f),
                        "version": p.get("version"), "name": p.get("name")}
    return out


def load(protocol_id: str) -> dict:
    entry = list_protocols().get(protocol_id)
    if not entry:
        raise ValueError(f"unknown protocol: {protocol_id}")
    return load_file(Path(entry["path"]))


def match_trigger(text: str) -> list[str]:
    """Return ids whose trigger phrases appear in text (case-insensitive)."""
    low = text.lower()
    hits = []
    for pid, entry in list_protocols().items():
        p = load_file(Path(entry["path"]))
        if any(t.lower() in low for t in p.get("triggers", [])):
            hits.append(pid)
    return hits
