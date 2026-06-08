"""XDG directory layout. State (vault, keys, passport, audit, quarantine)
lives outside any repo and is per-machine."""
import os
from pathlib import Path


def _xdg(env: str, default: str) -> Path:
    return Path(os.environ.get(env, str(Path.home() / default)))


STATE_DIR = _xdg("XDG_STATE_HOME", ".local/state") / "sdg"
CONFIG_DIR = _xdg("XDG_CONFIG_HOME", ".config") / "sdg"
DATA_DIR = _xdg("XDG_DATA_HOME", ".local/share") / "sdg"

VAULT_DB = STATE_DIR / "vault.db"
VAULT_KEY = STATE_DIR / "vault.key"
PASSPORT = STATE_DIR / "passport.json"
AUDIT_DIR = STATE_DIR / "audit"
QUARANTINE_DIR = STATE_DIR / "quarantine"
CONV_DIR = STATE_DIR / "conversations"


def ensure_state() -> None:
    for d in (STATE_DIR, AUDIT_DIR, QUARANTINE_DIR, CONV_DIR):
        d.mkdir(parents=True, exist_ok=True)
    try:
        STATE_DIR.chmod(0o700)
    except OSError:
        pass
