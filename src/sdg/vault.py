"""Encrypted pseudonym mapping vault.

SQLite store; original values encrypted with Fernet. Key in a separate 0600
file. Pseudonyms are stable per value within a session so the AI can reason
coherently (same person -> same [PERSON_NNN] everywhere).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from cryptography.fernet import Fernet

from . import paths


class Vault:
    def __init__(self, db: Path | None = None, key: Path | None = None,
                 label_map: dict[str, str] | None = None):
        paths.ensure_state()
        db = db or paths.VAULT_DB
        key = key or paths.VAULT_KEY
        if not key.exists():
            key.write_bytes(Fernet.generate_key())
            key.chmod(0o600)
        elif (key.stat().st_mode & 0o077) != 0:
            raise PermissionError(
                f"vault key {key} has loose permissions; run: chmod 600 {key}")
        self.fernet = Fernet(key.read_bytes())
        self.label_map = label_map or {}
        self.con = sqlite3.connect(db)
        self.con.execute("""CREATE TABLE IF NOT EXISTS mapping (
            pseudonym TEXT PRIMARY KEY,
            etype TEXT NOT NULL,
            value_enc BLOB NOT NULL)""")
        self._reverse = {}
        for ps, vc in self.con.execute("SELECT pseudonym, value_enc FROM mapping"):
            self._reverse[self.fernet.decrypt(vc).decode()] = ps

    def pseudonym(self, value: str, etype: str) -> str:
        if value in self._reverse:
            return self._reverse[value]
        label = self.label_map.get(etype, "DATA")
        n = 1 + self.con.execute(
            "SELECT COUNT(*) FROM mapping WHERE etype = ?", (etype,)).fetchone()[0]
        ps = f"[{label}_{n:03d}]"
        self.con.execute("INSERT INTO mapping VALUES (?,?,?)",
                         (ps, etype, self.fernet.encrypt(value.encode())))
        self.con.commit()
        self._reverse[value] = ps
        return ps

    def restore(self, text: str) -> str:
        for ps, vc in self.con.execute("SELECT pseudonym, value_enc FROM mapping"):
            text = text.replace(ps, self.fernet.decrypt(vc).decode())
        return text

    def close(self):
        self.con.close()
