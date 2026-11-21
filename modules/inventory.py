"""System inventory via psutil — no console."""

from __future__ import annotations

import os
import platform
import socket

import psutil


def _disk_status(usage_percent: float) -> str:
    if usage_percent >= 95:
        return "Critical"
    if usage_percent >= 85:
        return "High"
    if usage_percent >= 70:
        return "Warning"
    return "Healthy"


def get_inventory() -> dict:
    uname = platform.uname()
    cpu_name = uname.processor or platform.processor() or "CPU"
    if not cpu_name or cpu_name == "":
        cpu_name = platform.machine()

    # Better CPU name on Windows via registry-free WMI alternative: skip (silent)
    try:
        import cpuinfo  # optional
        cpu_name = cpuinfo.get_cpu_info().get("brand_raw", cpu_name)
    except Exception:
        pass

    # psutil cpu percent (brief sample)
    cpu_usage = psutil.cpu_percent(interval=0.4)
    mem = psutil.virtual_memory()

    disks = []
    for part in psutil.disk_partitions(all=False):
        if os.name == "nt":
            if "cdrom" in part.opts.lower() or part.fstype == "":
                continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            continue
        total_gb = round(usage.total / (1024**3), 2)
        used_gb = round(usage.used / (1024**3), 2)
        free_gb = round(usage.free / (1024**3), 2)
        pct = round(usage.percent, 1)
        disks.append(
            {
                "device": part.device,
                "mountpoint": part.mountpoint,
                "filesystem": part.fstype or "unknown",
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "usage_percent": pct,
                "status": _disk_status(pct),
            }
        )

    system = {
        "computer_name": socket.gethostname(),
        "username": os.environ.get("USERNAME") or os.environ.get("USER") or "user",
        "os": {
            "name": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
        },
    }

    cpu = {
        "name": cpu_name,
        "physical_cores": psutil.cpu_count(logical=False) or 1,
        "logical_cores": psutil.cpu_count(logical=True) or 1,
        "usage_percent": round(cpu_usage, 1),
    }

    ram = {
        "total_gb": round(mem.total / (1024**3), 2),
        "available_gb": round(mem.available / (1024**3), 2),
        "usage_percent": round(mem.percent, 1),
    }

    return {"system": system, "cpu": cpu, "ram": ram, "disk": disks}
