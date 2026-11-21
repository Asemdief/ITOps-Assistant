"""
ITOps Command — opt-in, reversible security fixes.

Contract:
  * Nothing here runs during a scan. The UI calls apply_fix() only after the
    user explicitly chooses a finding.
  * dry_run=True is the DEFAULT: returns exactly what would change.
  * Every applied change is written to a journal (previous value included)
    in the per-user data dir, and can be undone with rollback().
  * Registry DWORD fixes only (small, auditable, reversible). Anything that
    cannot be reversed does not belong in this module.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any

from modules.paths import get_data_dir
from modules.registry_io import WinRegistry, is_admin

JOURNAL_NAME = "security_journal.jsonl"


def _journal_path(journal_path: str | None) -> str:
    return journal_path or os.path.join(get_data_dir(), JOURNAL_NAME)


def _read_journal(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def _append_journal(path: str, entry: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def apply_fix(
    finding: dict[str, Any],
    *,
    dry_run: bool = True,
    reg=None,
    admin: bool | None = None,
    journal_path: str | None = None,
) -> dict[str, Any]:
    fix = finding.get("fix")
    if not fix or fix.get("kind") != "registry_dword":
        return {"ok": False, "status": "NO_FIX", "message": "No safe automatic fix for this finding."}

    reg = reg or WinRegistry()
    admin = is_admin() if admin is None else admin
    if fix.get("needs_admin") and not admin:
        return {"ok": False, "status": "NEEDS_ADMIN", "message": "Run ITOps Command as administrator to apply this fix."}

    hive, path, name, new = fix["hive"], fix["path"], fix["name"], int(fix["value"])
    prev = reg.get(hive, path, name)
    if prev is not None and not isinstance(prev, int):
        return {"ok": False, "status": "UNEXPECTED_TYPE",
                "message": f"Existing value is not a DWORD ({type(prev).__name__}); refusing to overwrite."}

    plan = {
        "finding_id": finding["id"],
        "target": f"{hive}\\{path}\\{name}",
        "previous": prev,
        "new": new,
        "impact": fix.get("impact", ""),
        "reboot_required": bool(fix.get("reboot_required")),
    }
    if prev == new:
        return {"ok": True, "status": "ALREADY_SET", "plan": plan, "message": "Already at the target value."}
    if dry_run:
        return {"ok": True, "status": "DRY_RUN", "plan": plan, "message": "Preview only — nothing was changed."}

    jp = _journal_path(journal_path)
    reg.set_dword(hive, path, name, new)
    if reg.get(hive, path, name) != new:
        return {"ok": False, "status": "VERIFY_FAILED", "plan": plan, "message": "Value did not stick (blocked by policy?)."}

    entry_id = uuid.uuid4().hex[:10]
    _append_journal(jp, {
        "type": "apply", "id": entry_id, "ts": datetime.now().isoformat(timespec="seconds"),
        "finding_id": finding["id"], "hive": hive, "path": path, "name": name,
        "previous": prev, "new": new, "reboot_required": plan["reboot_required"],
    })
    return {"ok": True, "status": "APPLIED", "entry_id": entry_id, "plan": plan,
            "message": "Applied. You can undo this from the change history."}


def list_journal(journal_path: str | None = None) -> list[dict]:
    """Applied changes with an `undone` flag, newest first."""
    rows = _read_journal(_journal_path(journal_path))
    undone = {r["rollback_of"] for r in rows if r.get("type") == "rollback"}
    applied = [dict(r, undone=r["id"] in undone) for r in rows if r.get("type") == "apply"]
    return list(reversed(applied))


def rollback(
    entry_id: str,
    *,
    reg=None,
    admin: bool | None = None,
    journal_path: str | None = None,
) -> dict[str, Any]:
    reg = reg or WinRegistry()
    admin = is_admin() if admin is None else admin
    jp = _journal_path(journal_path)
    entry = next((e for e in list_journal(jp) if e["id"] == entry_id), None)
    if entry is None:
        return {"ok": False, "status": "NOT_FOUND", "message": "No such change in the journal."}
    if entry["undone"]:
        return {"ok": False, "status": "ALREADY_UNDONE", "message": "This change was already rolled back."}
    if entry["hive"] == "HKLM" and not admin:
        return {"ok": False, "status": "NEEDS_ADMIN", "message": "Run as administrator to roll this back."}

    if entry["previous"] is None:
        reg.delete_value(entry["hive"], entry["path"], entry["name"])
    else:
        reg.set_dword(entry["hive"], entry["path"], entry["name"], int(entry["previous"]))
    _append_journal(jp, {"type": "rollback", "rollback_of": entry_id,
                         "ts": datetime.now().isoformat(timespec="seconds")})
    return {"ok": True, "status": "ROLLED_BACK", "message": "Previous value restored."}
