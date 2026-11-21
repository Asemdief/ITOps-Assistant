"""
Safe auto-fix — ALL actions silent (no CMD / PowerShell window).
Never launches cleanmgr or any visible UI.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from modules.win_silent import run_powershell, run_silent


def _ok(action: str, details: str) -> dict:
    return {"action": action, "success": True, "details": details}


def _fail(action: str, details: str) -> dict:
    return {"action": action, "success": False, "details": details}


def clean_user_temp() -> dict:
    action = "Clean user TEMP folder"
    temp = os.environ.get("TEMP") or tempfile.gettempdir()
    deleted = 0
    skipped = 0
    try:
        root = Path(temp)
        if not root.is_dir():
            return _fail(action, f"TEMP not found: {temp}")
        for item in list(root.iterdir())[:2000]:
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink(missing_ok=True)
                    deleted += 1
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                    deleted += 1
            except OSError:
                skipped += 1
        return _ok(action, f"Deleted {deleted} items (skipped {skipped} locked)")
    except Exception as e:
        return _fail(action, str(e))


def flush_dns() -> dict:
    action = "Flush DNS cache"
    try:
        r = run_silent(["ipconfig", "/flushdns"], timeout=20)
        out = (r.stdout or r.stderr or "").strip() or "DNS cache flushed"
        return _ok(action, out[:240]) if r.returncode == 0 else _fail(action, out[:240])
    except Exception as e:
        return _fail(action, str(e))


def empty_recycle_bin() -> dict:
    action = "Empty Recycle Bin"
    try:
        script = (
            "$ErrorActionPreference='SilentlyContinue'; "
            "Clear-RecycleBin -Force -ErrorAction SilentlyContinue; "
            "'Recycle Bin cleared'"
        )
        r = run_powershell(script, timeout=45)
        out = (r.stdout or r.stderr or "").strip() or "Done"
        if r.returncode == 0:
            return _ok(action, out[:200])
        return _fail(action, out[:200] or "Failed (may need Admin or already empty)")
    except Exception as e:
        return _fail(action, str(e))


def clear_dns_client_cache() -> dict:
    action = "Clear DNS client cache"
    try:
        r = run_powershell("Clear-DnsClientCache -ErrorAction SilentlyContinue; 'OK'", timeout=20)
        if r.returncode == 0:
            return _ok(action, "DNS client cache cleared")
        return _fail(action, (r.stderr or r.stdout or "failed")[:200])
    except Exception as e:
        return _fail(action, str(e))


def run_auto_fixes(root_cause: dict | None = None) -> list[dict]:
    results: list[dict] = []
    issues = []
    status = ""
    if isinstance(root_cause, dict):
        issues = [str(x).lower() for x in (root_cause.get("issues") or [])]
        status = str(root_cause.get("status", "")).lower()

    results.append(clean_user_temp())
    results.append(flush_dns())

    need_disk = any("disk" in i or "space" in i or "usage" in i for i in issues)
    need_net = any(
        x in i for i in issues for x in ("internet", "network", "dns", "gateway", "connectivity")
    ) or ("issue" in status and "healthy" not in status)

    if need_disk:
        results.append(empty_recycle_bin())
    if need_net:
        results.append(clear_dns_client_cache())

    return results
