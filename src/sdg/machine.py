"""Machine technical-audit probes: RAM, disk, disk encryption, Ollama bind,
vault-key permissions. Cross-platform, best-effort; unknown results are
reported honestly rather than assumed-pass.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys

from . import paths


def _r(ok, status, detail, remediation=""):
    return {"ok": ok, "status": status, "detail": detail, "remediation": remediation}


def ram_gb() -> float | None:
    try:
        return round(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
                     / 1024**3, 1)
    except (ValueError, AttributeError, OSError):
        return None


def check_ram(min_gb: int = 16) -> dict:
    gb = ram_gb()
    if gb is None:
        return _r(False, "warn", "RAM unknown", "verify manually")
    if gb >= 32:
        return _r(True, "ok", f"{gb} GB (supports 27B models)")
    if gb >= min_gb:
        return _r(True, "warn", f"{gb} GB (8-12B models only)",
                  "32 GB recommended for the 27B model")
    return _r(False, "fail", f"{gb} GB < {min_gb} GB", "add RAM; local path disabled")


def check_disk(min_free_gb: int = 25) -> dict:
    free = shutil.disk_usage(str(paths.STATE_DIR.parent if paths.STATE_DIR.exists()
                                 else os.path.expanduser("~"))).free / 1024**3
    if free >= min_free_gb:
        return _r(True, "ok", f"{free:.0f} GB free")
    return _r(False, "warn", f"{free:.0f} GB free < {min_free_gb} GB",
              "free disk space for the local model")


def check_disk_encryption() -> dict:
    s = platform.system()
    try:
        if s == "Darwin":
            out = subprocess.run(["fdesetup", "status"], capture_output=True,
                                 text=True, timeout=10).stdout
            if "FileVault is On" in out:
                return _r(True, "ok", "FileVault on")
            return _r(False, "fail", "FileVault off",
                      "enable FileVault; ALL PII paths disabled")
        if s == "Linux":
            out = subprocess.run(["lsblk", "-o", "TYPE", "-n"],
                                 capture_output=True, text=True, timeout=10).stdout
            if "crypt" in out:
                return _r(True, "ok", "LUKS-encrypted volume detected")
            return _r(False, "fail", "no LUKS volume detected",
                      "enable LUKS; ALL PII paths disabled")
        if s == "Windows":
            out = subprocess.run(["manage-bde", "-status"], capture_output=True,
                                 text=True, timeout=15).stdout
            if "Percentage Encrypted: 100" in out or "Protection On" in out:
                return _r(True, "ok", "BitLocker on")
            return _r(False, "fail", "BitLocker not confirmed (experimental)",
                      "enable BitLocker; ALL PII paths disabled")
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        return _r(False, "warn", f"disk encryption undetermined ({e})",
                  "verify disk encryption manually; PII paths disabled until confirmed")
    return _r(False, "warn", f"unsupported OS {s} for encryption probe", "")


def check_ollama_bind() -> dict:
    """Confirm Ollama listens only on localhost (not 0.0.0.0)."""
    s = platform.system()
    try:
        if s in ("Darwin", "Linux"):
            out = subprocess.run(
                ["lsof", "-nP", "-iTCP:11434", "-sTCP:LISTEN"],
                capture_output=True, text=True, timeout=10).stdout
            if not out.strip():
                return _r(False, "warn", "Ollama not listening on 11434",
                          "start Ollama; local path disabled")
            if "127.0.0.1:11434" in out and "*:11434" not in out and \
               "0.0.0.0:11434" not in out:
                return _r(True, "ok", "Ollama bound to 127.0.0.1 only")
            return _r(False, "fail", "Ollama bound to a non-local address",
                      "set OLLAMA_HOST=127.0.0.1:11434; local path disabled")
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        return _r(False, "warn", f"bind undetermined ({e})", "verify Ollama bind")
    return _r(False, "warn", f"unsupported OS {s} for bind probe", "")


def check_vault_key() -> dict:
    key = paths.VAULT_KEY
    if not key.exists():
        return _r(True, "ok", "vault key not yet created (will be 0600)")
    mode = key.stat().st_mode & 0o777
    if mode & 0o077:
        return _r(False, "fail", f"vault key mode {oct(mode)} too open",
                  f"chmod 600 {key}; ALL PII paths disabled")
    return _r(True, "ok", "vault key 0600")


def run_all() -> dict:
    return {
        "ram": check_ram(),
        "disk": check_disk(),
        "disk_encryption": check_disk_encryption(),
        "ollama_bind": check_ollama_bind(),
        "vault_key": check_vault_key(),
    }
