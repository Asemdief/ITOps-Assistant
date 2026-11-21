"""Top processes via psutil — fast, no console."""

from __future__ import annotations

import psutil

IGNORE = {
    "system idle process",
    "idle",
    "itops-assistant.exe",
    "itops-assistant",
    "system",
    "registry",
    "memory compression",
}


def get_top_processes(limit: int = 5) -> dict:
    # Prime CPU counters quickly
    for p in psutil.process_iter(["pid"]):
        try:
            p.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    psutil.cpu_percent(interval=0.15)

    refreshed = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = p.info
            name = (info.get("name") or "").strip()
            if not name or name.lower() in IGNORE:
                continue
            refreshed.append(
                {
                    "name": name,
                    "pid": info.get("pid"),
                    "cpu_percent": float(info.get("cpu_percent") or 0.0),
                    "memory_percent": float(info.get("memory_percent") or 0.0),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    by_cpu = sorted(refreshed, key=lambda x: x["cpu_percent"], reverse=True)[:limit]
    by_ram = sorted(refreshed, key=lambda x: x["memory_percent"], reverse=True)[:limit]
    return {"top_cpu": by_cpu, "top_ram": by_ram}
