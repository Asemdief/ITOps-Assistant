import psutil


def get_process_info(top_n=5):
    """
    Collect and analyze running processes.

    Returns the top processes by normalized CPU usage
    and memory usage.
    """

    processes = []

    # First pass: initialize CPU counters
    for process in psutil.process_iter(
        ["pid", "name", "memory_percent"]
    ):
        try:
            process.cpu_percent(interval=None)
        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess
        ):
            continue

    # Give Windows time to calculate CPU usage
    psutil.cpu_percent(interval=0.5)

    # Second pass: collect actual values
    for process in psutil.process_iter(
        ["pid", "name", "memory_percent"]
    ):
        try:
            cpu_percent = process.cpu_percent(interval=None)

            memory_percent = process.info.get(
                "memory_percent",
                0.0
            ) or 0.0

            name = process.info.get(
                "name"
            ) or "Unknown"

            pid = process.info.get(
                "pid"
            )

            # Normalize CPU against total logical CPUs.
            logical_cpus = psutil.cpu_count(
                logical=True
            ) or 1

            normalized_cpu = cpu_percent / logical_cpus

            processes.append({
                "pid": pid,
                "name": name,
                "cpu_percent": round(
                    normalized_cpu, 1
                ),
                "memory_percent": round(
                    memory_percent, 2
                )
            })

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess
        ):
            continue

    top_cpu = sorted(
        processes,
        key=lambda p: p["cpu_percent"],
        reverse=True
    )[:top_n]

    top_memory = sorted(
        processes,
        key=lambda p: p["memory_percent"],
        reverse=True
    )[:top_n]

    return {
        "top_cpu": top_cpu,
        "top_memory": top_memory
    }