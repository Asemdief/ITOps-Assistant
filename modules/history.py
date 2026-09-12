import json
import os
from datetime import datetime
from modules.paths import get_app_dir


HISTORY_FILE = "last_report.json"


def _get_history_path():
    """Return path to history file (next to .exe or project root)."""
    return os.path.join(get_app_dir(), HISTORY_FILE)


def save_report(data):
    """
    Save a lightweight snapshot of the current report.
    """
    snapshot = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "computer_name": data["system"].get("computer_name"),
        "cpu_usage": data["cpu"].get("usage_percent"),
        "ram_usage": data["ram"].get("usage_percent"),
        "disk": [
            {
                "device": d["device"],
                "usage_percent": d["usage_percent"],
                "status": d["status"]
            }
            for d in data.get("disk", [])
        ],
        "network": {
            "adapter": data["network"].get("adapter"),
            "ip": data["network"].get("ip"),
            "status": data["network"].get("status"),
            "gateway_latency": data["network"].get("gateway_latency", {}).get("avg_ms"),
            "internet_latency": data["network"].get("internet_latency", {}).get("avg_ms"),
        },
        "health_score": data["health"].get("score"),
    }

    try:
        path = _get_history_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
    except OSError:
        pass  # Fail silently if can't write


def load_previous_report():
    """
    Load the previous report snapshot if it exists.
    """
    path = _get_history_path()
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def compare_reports(current_data, previous):
    """
    Compare current data with previous snapshot.
    Returns a list of human-readable change messages.
    """
    if not previous:
        return []

    changes = []

    # CPU
    curr_cpu = current_data["cpu"].get("usage_percent", 0)
    prev_cpu = previous.get("cpu_usage", 0)
    diff_cpu = curr_cpu - prev_cpu
    if abs(diff_cpu) >= 10:
        direction = "↑" if diff_cpu > 0 else "↓"
        changes.append(f"CPU usage {direction} {abs(diff_cpu):.1f}%  ({prev_cpu}% → {curr_cpu}%)")

    # RAM
    curr_ram = current_data["ram"].get("usage_percent", 0)
    prev_ram = previous.get("ram_usage", 0)
    diff_ram = curr_ram - prev_ram
    if abs(diff_ram) >= 8:
        direction = "↑" if diff_ram > 0 else "↓"
        changes.append(f"RAM usage {direction} {abs(diff_ram):.1f}%  ({prev_ram}% → {curr_ram}%)")

    # Disks
    prev_disks = {d["device"]: d for d in previous.get("disk", [])}
    for disk in current_data.get("disk", []):
        device = disk["device"]
        curr_usage = disk["usage_percent"]
        if device in prev_disks:
            prev_usage = prev_disks[device]["usage_percent"]
            diff = curr_usage - prev_usage
            if abs(diff) >= 3:
                direction = "↑" if diff > 0 else "↓"
                changes.append(
                    f"{device} usage {direction} {abs(diff):.1f}%  ({prev_usage}% → {curr_usage}%)"
                )

    # Latency
    curr_net = current_data.get("network", {})
    prev_net = previous.get("network", {})

    curr_gw = curr_net.get("gateway_latency", {}).get("avg_ms")
    prev_gw = prev_net.get("gateway_latency")
    if curr_gw is not None and prev_gw is not None and abs(curr_gw - prev_gw) >= 5:
        direction = "↑" if curr_gw > prev_gw else "↓"
        changes.append(f"Gateway latency {direction} {abs(curr_gw - prev_gw):.0f} ms")

    curr_inet = curr_net.get("internet_latency", {}).get("avg_ms")
    prev_inet = prev_net.get("internet_latency")
    if curr_inet is not None and prev_inet is not None and abs(curr_inet - prev_inet) >= 15:
        direction = "↑" if curr_inet > prev_inet else "↓"
        changes.append(f"Internet latency {direction} {abs(curr_inet - prev_inet):.0f} ms")

    # Health score
    curr_score = current_data["health"].get("score", 0)
    prev_score = previous.get("health_score", 0)
    if curr_score != prev_score:
        direction = "↑" if curr_score > prev_score else "↓"
        changes.append(f"Health score {direction} {abs(curr_score - prev_score)} points  ({prev_score} → {curr_score})")

    return changes
