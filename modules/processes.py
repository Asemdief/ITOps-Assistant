import psutil
import time


# Processes to always ignore in reports
IGNORE_PROCESSES = {
    "system idle process",
    "system",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
    "fontdrvhost.exe",
    "dwm.exe",
    "conhost.exe",
    "runtimebroker.exe",
    "sihost.exe",
    "taskhostw.exe",
    "searchindexer.exe",
    "searchhost.exe",
    "startmenuexperiencehost.exe",
    "shellexperiencehost.exe",
    "textinputhost.exe",
    "itops-assistant.exe",  # ourselves
}


def get_top_processes(limit=5):
    """
    Return top processes by CPU and by RAM.
    Filters out noisy system processes and flags high consumers.
    """
    processes = []

    # First pass to initialize cpu_percent
    for process in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            process.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    time.sleep(0.35)

    for process in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            name = (process.info["name"] or "Unknown").strip()
            name_lower = name.lower()

            # Skip ignored system noise
            if name_lower in IGNORE_PROCESSES:
                continue

            cpu_percent = process.cpu_percent(interval=None)
            memory_percent = process.info["memory_percent"] or 0.0

            # Skip processes with almost zero impact
            if cpu_percent < 0.5 and memory_percent < 0.5:
                continue

            high_cpu = cpu_percent >= 50
            high_ram = memory_percent >= 12

            processes.append({
                "pid": process.info["pid"],
                "name": name,
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory_percent, 2),
                "high_cpu": high_cpu,
                "high_ram": high_ram
            })

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    top_cpu = sorted(processes, key=lambda x: x["cpu_percent"], reverse=True)[:limit]
    top_ram = sorted(processes, key=lambda x: x["memory_percent"], reverse=True)[:limit]

    # Collect any high consumers for warnings
    warnings = []
    for p in processes:
        if p["high_cpu"]:
            warnings.append(f"High CPU: {p['name']} ({p['cpu_percent']}%)")
        if p["high_ram"]:
            warnings.append(f"High RAM: {p['name']} ({p['memory_percent']}%)")

    return {
        "top_cpu": top_cpu,
        "top_ram": top_ram,
        "warnings": warnings[:5]   # max 5 warnings
    }
