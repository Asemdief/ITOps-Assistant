"""History compare/save next to the app — no console."""

from __future__ import annotations

import json
import os
from datetime import datetime

from modules.paths import get_app_dir


def _history_path() -> str:
    d = os.path.join(get_app_dir(), "reports")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "last_snapshot.json")


def load_previous_report() -> dict | None:
    path = _history_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def save_report(data: dict) -> None:
    path = _history_path()
    snap = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "cpu": data.get("cpu"),
        "ram": data.get("ram"),
        "disk": data.get("disk"),
        "health": data.get("health"),
        "network": data.get("network"),
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=2, ensure_ascii=False, default=str)
    except OSError:
        pass


def compare_reports(current: dict, previous: dict | None) -> list[str]:
    if not previous:
        return ["No previous report found (or no significant changes)"]

    changes: list[str] = []
    try:
        c_cpu = float((current.get("cpu") or {}).get("usage_percent") or 0)
        p_cpu = float((previous.get("cpu") or {}).get("usage_percent") or 0)
        d = c_cpu - p_cpu
        if abs(d) >= 5:
            arrow = "↑" if d > 0 else "↓"
            changes.append(f"CPU usage {arrow} {abs(d):.1f}%  ({p_cpu:.1f}% → {c_cpu:.1f}%)")

        c_ram = float((current.get("ram") or {}).get("usage_percent") or 0)
        p_ram = float((previous.get("ram") or {}).get("usage_percent") or 0)
        d = c_ram - p_ram
        if abs(d) >= 5:
            arrow = "↑" if d > 0 else "↓"
            changes.append(f"RAM usage {arrow} {abs(d):.1f}%  ({p_ram:.1f}% → {c_ram:.1f}%)")

        c_h = int((current.get("health") or {}).get("score") or 0)
        p_h = int((previous.get("health") or {}).get("score") or 0)
        d = c_h - p_h
        if abs(d) >= 3:
            arrow = "↑" if d > 0 else "↓"
            changes.append(f"Health score {arrow} {abs(d)} points  ({p_h} → {c_h})")

        prev_disks = {d.get("device"): d for d in (previous.get("disk") or [])}
        for d in current.get("disk") or []:
            dev = d.get("device")
            if dev not in prev_disks:
                continue
            c_u = float(d.get("usage_percent") or 0)
            p_u = float(prev_disks[dev].get("usage_percent") or 0)
            delta = c_u - p_u
            if abs(delta) >= 2:
                arrow = "↑" if delta > 0 else "↓"
                changes.append(
                    f"{dev} usage {arrow} {abs(delta):.1f}%  ({p_u:.1f}% → {c_u:.1f}%)"
                )
    except (TypeError, ValueError):
        pass

    if not changes:
        return ["No significant changes since last run"]
    return changes
